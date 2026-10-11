"""Real private D-Bus protocol tests; fake portal, no compositor/camera/input grants."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux portal protocol")
@pytest.mark.parametrize("case", ["missing", "denied", "no_pointer", "no_shortcut", "coordinates",
                                  "cancel", "success", "owner_lost", "shortcut_changed", "worker"])
def test_private_portal_protocol(case):
    if not shutil.which("dbus-run-session"):
        pytest.fail("Linux protocol tests require dbus-run-session; do not silently skip safety evidence")
    result = subprocess.run(["dbus-run-session", "--", sys.executable, str(Path(__file__).resolve()), case],
                            env={**os.environ, "XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "portal-test"},
                            capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stdout + result.stderr


async def scenario(case):
    import asyncio
    import threading
    import time
    from dbus_next import Message, MessageType, Variant
    from dbus_next.aio import MessageBus
    from mouse_invisivel.wayland import (PortalConnection, PortalError, SERVICE, PATH, REMOTE,
                                        SHORTCUTS, SCREENCAST, SESSION, REQUEST, STOP_ID, values)
    fake = await MessageBus().connect()
    await fake.request_name(SERVICE)
    events, requests, closes = [], [], []
    remote_path, shortcut_path = PATH + "/session/test/remote", PATH + "/session/test/shortcut"

    def signal(path, interface, member, signature, body):
        fake.send(Message.new_signal(path, interface, member, signature, body))

    def handle(message):
        if message.message_type != MessageType.METHOD_CALL:
            return
        if message.interface == "org.freedesktop.DBus.Properties":
            interface = message.body[0]
            props = ({"version": Variant("u", 2), "AvailableDeviceTypes": Variant("u", 2)}
                     if interface == REMOTE and case != "missing" else
                     {"version": Variant("u", 1)} if interface == SHORTCUTS else
                     {"version": Variant("u", 3), "AvailableSourceTypes": Variant("u", 1)}
                     if interface == SCREENCAST else {})
            return Message.new_method_return(message, "a{sv}", [props])
        if message.interface in (SESSION, REQUEST) and message.member == "Close":
            closes.append(message.path)
            return Message.new_method_return(message)
        if message.member.startswith("Notify"):
            events.append((message.member, values(message.body)))
            return Message.new_method_return(message)
        if message.interface not in (REMOTE, SHORTCUTS, SCREENCAST):
            return
        opts = values(message.body[-1])
        requests.append((message.interface, message.member, values(message.body)))
        sender = message.sender[1:].replace(".", "_")
        path = f"{PATH}/request/{sender}/{opts['handle_token']}"
        response, data = 0, {}
        if message.member == "CreateSession":
            data = {"session_handle": Variant("s", remote_path if message.interface == REMOTE else shortcut_path)}
        elif message.member == "SelectDevices":
            assert opts["types"] == 2 and opts["persist_mode"] == 0
            assert "restore_token" not in opts
        elif message.member == "SelectSources":
            assert opts["types"] == 1 and opts["multiple"] is True and "persist_mode" not in opts
        elif message.member == "Start":
            response = 1 if case == "denied" else 0
            data = {"devices": Variant("u", 0 if case == "no_pointer" else 2),
                    "streams": Variant("a(ua{sv})", [[101, {
                        "position": Variant("(ii)", [-1600, 0]), "size": Variant("(ii)", [1600, 900]),
                        "source_type": Variant("u", 1)}], [102, {
                        "position": Variant("(ii)", [-1600, 0]), "size": Variant("(ii)", [1600, 900]),
                        "source_type": Variant("u", 1)}]])}
            if case == "coordinates":
                data["streams"] = Variant("a(ua{sv})", [[101, {"size": Variant("(ii)", [1600, 900])}]])
        elif message.member == "BindShortcuts":
            assert message.body[1][0][0] == STOP_ID
            data = {"shortcuts": Variant("a(sa{sv})", [] if case == "no_shortcut" else
                    [[STOP_ID, {"trigger_description": Variant("s", "Ctrl+Alt+Shift+Esc (mock)")}]])}
        else:
            raise AssertionError(message.member)
        # Deliver Response before returning the handle to expose subscription races.
        if not (case == "cancel" and message.member == "Start"):
            signal(path, REQUEST, "Response", "ua{sv}", [response, data])
        return Message.new_method_return(message, "o", [path])

    fake.add_message_handler(handle)
    stop = threading.Event()
    emergency, failures = [], []
    client = PortalConnection(stop, lambda: emergency.append("stop"), failures.append)
    try:
        await client.connect()
        if case == "package":
            process = await asyncio.create_subprocess_exec(sys.argv[2], "--check-portal",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(process.communicate(), 15)
            import json
            assert process.returncode == 0, stderr.decode()
            info = json.loads(stdout)
            assert info["available"] and info["consent_requested"] is False and not requests
            print("Frozen portal probe: real private D-Bus, fake backend, no input/consent")
            return
        if case == "worker":
            from mouse_invisivel.input_worker import InputSupervisor
            supervisor = InputSupervisor()
            try:
                async def until(condition, seconds=6):
                    deadline = time.monotonic()+seconds
                    while not condition():
                        supervisor.poll()
                        assert time.monotonic() < deadline, "Portal worker did not reach expected state"
                        await asyncio.sleep(.01)
                await until(lambda: supervisor.ready)
                assert supervisor.screens[1].map((.5, .5)) == (-800, 450, 102)
                try:
                    supervisor.activate()
                    raise AssertionError("Activation before physical-shortcut verification accepted")
                except RuntimeError:
                    pass
                signal(PATH, SHORTCUTS, "Activated", "osta{sv}", [shortcut_path, STOP_ID, 1, {}])
                await until(lambda: supervisor.emergency_verified)
                supervisor.activate()
                await asyncio.sleep(.04)
                supervisor.publish(time.monotonic(), ["drag"], supervisor.screens[1].map((.5, .5)), 3)
                await until(lambda: any(e[0] == "NotifyPointerButton" and e[1][-1] == 1 for e in events))
                move = next(e for e in events if e[0] == "NotifyPointerMotionAbsolute")
                assert move[1][-3:] == [102, 800., 450.]
                # No new batches: production watchdog must release the owned drag.
                await until(lambda: any(e[0] == "NotifyPointerButton" and e[1][-1] == 0 for e in events))
                await until(lambda: supervisor.token is None)
                supervisor.activate()
                await asyncio.sleep(.04)
                supervisor.publish(time.monotonic(), ["drag"], None, 3)
                await until(lambda: sum(e[0] == "NotifyPointerButton" and e[1][-1] == 1 for e in events) == 2)
                # Stop-binding loss disarms, but remote pointer consent still exists:
                # cleanup must send release through that channel before Session.Close.
                signal(PATH, SHORTCUTS, "ShortcutsChanged", "oa(sa{sv})", [shortcut_path, []])
                await until(lambda: not supervisor.process.is_alive())
                assert sum(e[0] == "NotifyPointerButton" and e[1][-1] == 0 for e in events) == 2
                assert not supervisor.ready and supervisor.inhibit.is_set()
                assert supervisor.release_complete.is_set()
            finally:
                supervisor.pause()
                supervisor.stop.set()
                await asyncio.to_thread(supervisor.process.join, 5)
            assert remote_path in closes and shortcut_path in closes
            return
        info = await client.capabilities()
        assert info["consent_requested"] is False and not requests
        if case == "missing":
            assert not info["available"] and "RemoteDesktop POINTER" in info["missing"]
        if case == "cancel":
            asyncio.get_running_loop().call_later(.1, stop.set)
        if case not in ("success", "owner_lost", "shortcut_changed"):
            try:
                await client.authorize()
                raise AssertionError("Missing/denied/incomplete/cancelled authorization accepted")
            except PortalError:
                assert not client.active and not events and not emergency
            if case != "missing":
                assert remote_path in closes
            if case == "cancel":
                assert any("/request/" in p for p in closes)
            return
        screens = await client.authorize()
        if case == "owner_lost":
            await fake.release_name(SERVICE)
            await asyncio.sleep(.02)
            assert not client.active and failures and not emergency
            return
        if case == "shortcut_changed":
            signal(PATH, SHORTCUTS, "ShortcutsChanged", "oa(sa{sv})", [shortcut_path, []])
            await asyncio.sleep(.02)
            assert not client.active and failures and not emergency
            return
        assert screens[0].width == 1600 and screens[0].x == -1600
        # A mirrored output still carries a distinct selected stream identity.
        assert screens[1].map((.5, .5)) == (-800, 450, 102)
        await client.notify("NotifyPointerMotionAbsolute", "udd", [102, 800., 450.])
        assert events[-1][1] == [remote_path, {}, 102, 800., 450.]
        signal(PATH, SHORTCUTS, "Activated", "osta{sv}", [shortcut_path, "unrelated", 1, {}])
        await asyncio.sleep(.02)
        assert not emergency
        signal(PATH, SHORTCUTS, "Activated", "osta{sv}", [shortcut_path, STOP_ID, 1, {}])
        await asyncio.sleep(.02)
        assert emergency == ["stop"]
        signal(remote_path, SESSION, "Closed", "a{sv}", [{}])
        await asyncio.sleep(.02)
        assert not client.active and failures and emergency == ["stop"]
        try:
            await client.notify("NotifyPointerButton", "iu", [272, 1])
            raise AssertionError("Input after revocation accepted")
        except PortalError:
            pass
        assert not any(m == "OpenPipeWireRemote" for _, m, _ in requests)
    finally:
        await client.close()
        fake.disconnect()


if __name__ == "__main__":
    import asyncio
    # Spawned production workers import this module as __mp_main__, not __main__.
    asyncio.run(scenario(sys.argv[1]))
