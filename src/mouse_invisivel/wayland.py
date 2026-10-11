"""Consent-only XDG portals. No XWayland/uinput fallback, screen pixels or restore tokens.

RemoteDesktop's documented Notify methods are used, not EIS. ScreenCast is requested
only for absolute-coordinate stream metadata; OpenPipeWireRemote is never called.
"""
import asyncio
import threading
import uuid
from dbus_next import Message, MessageType, Variant
from dbus_next.aio import MessageBus
from .platforms import Monitor

SERVICE = "org.freedesktop.portal.Desktop"
PATH = "/org/freedesktop/portal/desktop"
REMOTE = "org.freedesktop.portal.RemoteDesktop"
SHORTCUTS = "org.freedesktop.portal.GlobalShortcuts"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
REQUEST = "org.freedesktop.portal.Request"
SESSION = "org.freedesktop.portal.Session"
STOP_ID = "mouse-stop"


class PortalError(RuntimeError):
    pass


def values(value):
    if isinstance(value, Variant):
        return values(value.value)
    if isinstance(value, dict):
        return {k: values(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [values(v) for v in value]
    return value


class PortalConnection:
    def __init__(self, stop=None, emergency=None, failure=None):
        self.bus = None
        self.stop_event, self.emergency = stop, emergency
        self.failure, self.invalidated = failure, False
        self.owner, self.sessions = None, []
        self.pending = {}
        self.remote_session = self.shortcut_session = None
        self.active = False
        self.remote_open = False
        self.closing = False
        self.reason = "Portal authorization not started"
        self.screens = []
        self.trigger = ""

    async def connect(self):
        self.bus = await asyncio.wait_for(MessageBus().connect(), 3)
        reply = await self.call("org.freedesktop.DBus", "GetNameOwner", "s", [SERVICE],
                                path="/org/freedesktop/DBus", destination="org.freedesktop.DBus")
        self.owner = reply[0]
        self.bus.add_message_handler(self.signal)
        for rule in (f"type='signal',sender='{SERVICE}'",
                     f"type='signal',sender='org.freedesktop.DBus',member='NameOwnerChanged',arg0='{SERVICE}'"):
            await self.call("org.freedesktop.DBus", "AddMatch", "s", [rule],
                            path="/org/freedesktop/DBus", destination="org.freedesktop.DBus")

    async def call(self, interface, member, signature="", body=None, *, path=PATH,
                   destination=SERVICE, timeout=2):
        reply = await asyncio.wait_for(self.bus.call(Message(destination=destination, path=path,
            interface=interface, member=member, signature=signature, body=body or [])), timeout)
        if reply.message_type == MessageType.ERROR:
            raise PortalError(f"{member}: {reply.error_name}: {reply.body[0] if reply.body else ''}")
        return reply.body

    async def capabilities(self):
        found, errors = {}, {}
        for interface in (REMOTE, SHORTCUTS, SCREENCAST):
            try:
                result = await self.call("org.freedesktop.DBus.Properties", "GetAll", "s", [interface])
                found[interface] = values(result[0])
                if not found[interface]:
                    errors[interface] = "Interface has no properties (backend unavailable)"
            except Exception as e:
                errors[interface] = str(e)
        required = []
        if not found.get(REMOTE, {}).get("AvailableDeviceTypes", 0) & 2:
            required.append("RemoteDesktop POINTER")
        if found.get(SHORTCUTS, {}).get("version", 0) < 1:
            required.append("GlobalShortcuts")
        if not found.get(SCREENCAST, {}).get("AvailableSourceTypes", 0) & 1:
            required.append("ScreenCast MONITOR metadata")
        return {"available": not required, "missing": required, "interfaces": found,
                "errors": errors, "consent_requested": False,
                "detail": "Portal capability only; explicit consent and physical stop test still required"
                if not required else "Missing portal backend capabilities: " + ", ".join(required)}

    def signal(self, message):
        if message.message_type != MessageType.SIGNAL:
            return
        if (message.sender == "org.freedesktop.DBus" and message.interface == "org.freedesktop.DBus"
                and message.member == "NameOwnerChanged"):
            if message.body[0] == SERVICE and message.body[2] != self.owner:
                self.remote_open = False
                self.invalidate("Portal service disappeared/restarted")
            return
        if message.sender != self.owner:
            return
        if message.interface == REQUEST and message.member == "Response":
            future = self.pending.get(message.path)
            if future and not future.done():
                future.set_result(message.body)
        elif (message.interface == SESSION and message.member == "Closed"
              and message.path in self.sessions and not self.closing):
            if message.path == self.remote_session:
                self.remote_open = False
            self.invalidate("Portal session revoked/closed by desktop")
        elif message.interface == SHORTCUTS and message.member == "Activated":
            if len(message.body) >= 2 and message.body[:2] == [self.shortcut_session, STOP_ID]:
                if self.emergency:
                    self.emergency()
        elif message.interface == SHORTCUTS and message.member == "ShortcutsChanged":
            if self.active and message.body and message.body[0] == self.shortcut_session:
                self.invalidate("Emergency shortcut changed; reauthorize and test it again")

    def invalidate(self, reason):
        self.active, self.reason = False, reason
        self.invalidated = True
        if self.failure:
            self.failure(reason)

    async def request(self, interface, member, signature, body, options, timeout=90):
        token = "mouse_" + uuid.uuid4().hex
        options = {**options, "handle_token": Variant("s", token)}
        sender = self.bus.unique_name[1:].replace(".", "_")
        path = f"{PATH}/request/{sender}/{token}"
        future = asyncio.get_running_loop().create_future()
        # Subscribe before the method call: a fast denial/response can precede its reply.
        self.pending[path] = future
        try:
            reply = await self.call(interface, member, signature, [*body, options])
            if reply != [path]:
                raise PortalError("Portal returned an unexpected request handle")
            deadline = asyncio.get_running_loop().time() + timeout
            while not future.done():
                if self.stop_event and self.stop_event.is_set():
                    raise PortalError("Portal authorization cancelled by app shutdown")
                if asyncio.get_running_loop().time() >= deadline:
                    raise PortalError("Portal consent timed out; no input authorized")
                await asyncio.sleep(.02)
            response, result = future.result()
            if response != 0:
                raise PortalError("Portal request denied/cancelled" if response == 1 else "Portal request failed")
            return values(result)
        finally:
            self.pending.pop(path, None)
            if not future.done():
                future.cancel()
                try:
                    await self.call(REQUEST, "Close", path=path)
                except Exception:
                    pass

    async def authorize(self):
        info = await self.capabilities()
        if not info["available"]:
            raise PortalError(info["detail"])
        try:
            result = await self.request(REMOTE, "CreateSession", "a{sv}", [],
                {"session_handle_token": Variant("s", "mouse_" + uuid.uuid4().hex)})
            self.remote_session = result["session_handle"]
            self.sessions.append(self.remote_session)
            devices = {"types": Variant("u", 2)}  # POINTER only; never keyboard injection.
            if info["interfaces"][REMOTE].get("version", 0) >= 2:
                devices["persist_mode"] = Variant("u", 0)
            await self.request(REMOTE, "SelectDevices", "oa{sv}", [self.remote_session], devices)
            await self.request(SCREENCAST, "SelectSources", "oa{sv}", [self.remote_session],
                               {"types": Variant("u", 1), "multiple": Variant("b", True)})
            started = await self.request(REMOTE, "Start", "osa{sv}", [self.remote_session, ""], {})
            if not started.get("devices", 0) & 2:
                raise PortalError("Pointer permission was not granted")
            self.remote_open = True
            self.screens = self.parse_screens(started.get("streams", []))
            result = await self.request(SHORTCUTS, "CreateSession", "a{sv}", [],
                {"session_handle_token": Variant("s", "mouse_" + uuid.uuid4().hex)})
            self.shortcut_session = result["session_handle"]
            self.sessions.append(self.shortcut_session)
            shortcuts = [[STOP_ID, {"description": Variant("s", "Parar Mouse Invisível"),
                                   "preferred_trigger": Variant("s", "CTRL+ALT+SHIFT+Escape")}]]
            bound = await self.request(SHORTCUTS, "BindShortcuts", "oa(sa{sv})sa{sv}",
                                       [self.shortcut_session, shortcuts, ""], {})
            for key, properties in bound.get("shortcuts", []):
                if key == STOP_ID:
                    self.trigger = properties.get("trigger_description", "")
            if not self.trigger:
                raise PortalError("Desktop did not bind/describe the emergency shortcut; input disabled")
            if self.invalidated:
                raise PortalError(self.reason)
            self.active, self.reason = True, "Authorized for this session only"
            return self.screens
        except BaseException:
            await self.close()
            raise

    @staticmethod
    def parse_screens(streams):
        result = []
        for node, props in streams:
            if not isinstance(node, int) or node <= 0 or props.get("source_type", 1) != 1:
                raise PortalError("Invalid/non-monitor portal stream")
            size, position = props.get("size"), props.get("position")
            if (not size or not position or len(size) != 2 or len(position) != 2
                    or not all(isinstance(v, int) for v in [*size, *position])
                    or not all(1 < v <= 65536 for v in size)):
                raise PortalError("Portal omitted valid compositor monitor coordinates; no pixel-size guessing")
            result.append(Monitor(f"Portal stream {node}", *position, *size, portal_stream=node))
        if not result or len({s.name for s in result}) != len(result):
            raise PortalError("Portal returned no unique monitor streams")
        return result

    async def notify(self, member, signature, payload, cleanup=False):
        if not self.active and not (cleanup and self.remote_open):
            raise PortalError(self.reason)
        await self.call(REMOTE, member, "oa{sv}" + signature,
                        [self.remote_session, {}, *payload], timeout=.15)

    async def close(self):
        self.closing = True
        self.remote_open = False
        self.active = False
        for path in reversed(self.sessions):
            try:
                await self.call(SESSION, "Close", path=path, timeout=.5)
            except Exception:
                pass  # Disconnect below also ends this client's sessions.
        self.sessions.clear()
        if self.bus:
            self.bus.disconnect()


async def probe():
    connection = PortalConnection()
    try:
        await connection.connect()
        return await connection.capabilities()
    except Exception as e:
        return {"available": False, "detail": f"Portal session bus/service unavailable: {e}",
                "consent_requested": False, "missing": ["Session bus/portal service"]}
    finally:
        await connection.close()


def probe_sync():
    return asyncio.run(probe())


class PortalAdapter:
    """Blocking worker interface with a separate asyncio thread for revocation/stop signals."""
    def __init__(self, emergency, stop, failure=None):
        self.held = set()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="PortalSignals", daemon=True)
        self.thread.start()
        self.portal = PortalConnection(stop, emergency, failure)
        try:
            self.run(self.portal.connect(), timeout=10)
            self.run(self.portal.authorize(), timeout=120)
        except BaseException:
            self.stop()
            raise

    def run(self, coroutine, timeout=2):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        try:
            return future.result(timeout)
        except BaseException:
            future.cancel()
            raise

    def monitors(self):
        return self.portal.screens

    def check(self):
        if not self.is_alive():
            raise PortalError(self.portal.reason)

    def is_alive(self):
        return self.thread.is_alive() and self.portal.active

    def move(self, xy):
        self.check()
        screen = next((s for s in self.monitors() if len(xy) == 3 and s.portal_stream == xy[2]
                       and s.x <= xy[0] < s.x+s.width and s.y <= xy[1] < s.y+s.height), None)
        if screen is None:
            raise PortalError("Pointer target outside consented monitors")
        node = screen.portal_stream
        self.run(self.portal.notify("NotifyPointerMotionAbsolute", "udd",
                                   [node, float(xy[0]-screen.x), float(xy[1]-screen.y)]))

    def press(self, button):
        self.check()
        self.held.add(button)
        self.run(self.portal.notify("NotifyPointerButton", "iu", [272 if button == "left" else 273, 1]))

    def release(self, button):
        if button in self.held:
            if self.portal.remote_open:
                self.run(self.portal.notify("NotifyPointerButton", "iu", [272 if button == "left" else 273, 0], cleanup=True))
            # A revoked/destroyed remote session has no valid input channel. Its
            # virtual input teardown belongs to the compositor; physical tests must
            # confirm cleanup. Never create a new session to release without consent.
            self.held.remove(button)

    def scroll(self, amount):
        self.check()
        # Linux wheel positive is down; the application uses positive for up.
        self.run(self.portal.notify("NotifyPointerAxisDiscrete", "ui", [0, -int(amount)]))

    def stop(self):
        if self.thread.is_alive():
            try:
                self.run(self.portal.close(), timeout=3)
            finally:
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.thread.join(timeout=2)
                if not self.thread.is_alive():
                    self.loop.close()
