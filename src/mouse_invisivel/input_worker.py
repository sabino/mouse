"""Separate-process input ownership with stale-command watchdog and global Esc stop."""
import multiprocessing as mp
from queue import Empty, Full
import time
from .platforms import make_adapter, monitors, is_wayland, Monitor

MAX_AGE = 0.25
WATCHDOG = 0.35


class Executor:
    def __init__(self, adapter):
        self.adapter = adapter
        self.held = set()

    def release_all(self):
        failures = []
        for button in list(self.held):
            try:
                self.adapter.release(button)
                self.held.remove(button)
            except Exception as e:
                failures.append(str(e))
        if failures:
            raise RuntimeError("Button release failed: " + "; ".join(failures))

    def execute(self, actions, xy, scroll_step):
        if xy is not None and any(a in ("pointer", "drag") for a in actions):
            self.adapter.move(xy)
        for action in actions:
            if action in ("click", "secondary"):
                button = "left" if action == "click" else "right"
                self.held.add(button)
                self.adapter.press(button)
                self.adapter.release(button)
                self.held.remove(button)
            elif action == "drag":
                if "left" not in self.held:
                    self.held.add("left")
                    self.adapter.press("left")
            elif action == "release":
                self.release_all()
            elif action in ("scroll_up", "scroll_down"):
                self.adapter.scroll(scroll_step * (1 if action == "scroll_up" else -1))


class WorkerState:
    """Pure command gate, used by the worker and deterministic safety tests."""
    def __init__(self, executor):
        self.executor = executor
        self.token = None
        self.last = -float("inf")

    def disarm(self):
        self.token = None
        self.executor.release_all()

    def arm(self, token, now):
        self.disarm()
        self.token, self.last = token, now

    def command(self, token, timestamp, now, actions, xy, scroll):
        if token != self.token or self.token is None:
            return False
        if not 0 <= now - timestamp <= MAX_AGE or timestamp <= self.last:
            self.disarm()
            return False
        self.last = timestamp
        self.executor.execute(actions, xy, scroll)
        return True

    def tick(self, now, inhibited):
        if self.token is not None and (inhibited or now - self.last > WATCHDOG):
            self.disarm()
            return True
        return False


def _worker(commands, status, inhibit, stop, epoch, release_complete):
    executor, listener, state = None, None, None
    def report(kind, detail):
        try:
            status.put_nowait((kind, detail))
        except Full:
            pass
    def emergency():
        inhibit.set()
        report("stop", "Global emergency stop received. Re-activation requires neutral.")
    def failed(reason):
        inhibit.set()
        report("error", reason)
    try:
        if is_wayland():
            from .wayland import PortalAdapter
            report("authorizing", "Approve pointer + monitor metadata and choose emergency shortcut in desktop portal dialogs. No persistent grant/screen pixels.")
            adapter = PortalAdapter(emergency, stop, failed)
            listener = adapter
            get_monitors = adapter.monitors
        else:
            adapter = make_adapter()
            from pynput import keyboard
            def on_press(key):
                if key == keyboard.Key.esc:
                    emergency()
            listener = keyboard.Listener(on_press=on_press)
            listener.start()
            listener.wait()
            get_monitors = monitors
        executor = Executor(adapter)
        state = WorkerState(executor)
        topology = get_monitors()
        if not topology:
            raise RuntimeError("No native display coordinates available")
        # Operator must verify Esc reception before first activation.
        report("monitors", [m.to_dict() for m in topology])
        trigger = adapter.portal.trigger if is_wayland() else "Esc"
        report("ready", f"Input backend ready. Physically press {trigger} once to verify global stop before activation.")
        last_check = time.monotonic()
        while not stop.is_set():
            now = time.monotonic()
            if not listener.is_alive():
                raise RuntimeError("Global emergency listener stopped; input disabled")
            if state.tick(now, inhibit.is_set()):
                report("paused", "Paused: watchdog, tracking timeout or explicit pause")
            if now - last_check > 0.5:
                adapter.check()
                if get_monitors() != topology:
                    raise RuntimeError("Display layout/DPI changed; pause and restart input diagnostics")
                last_check = now
            try:
                message = commands.get(timeout=0.02)
            except Empty:
                continue
            kind, token, timestamp, payload = message
            if token != epoch.value or inhibit.is_set():
                continue
            if now - timestamp > MAX_AGE or timestamp > time.monotonic():
                state.disarm()
                report("paused", "Stale input command discarded")
                continue
            if kind == "arm" and not inhibit.is_set():
                state.arm(token, timestamp)
                report("active", "Active; awaiting neutral gesture")
            elif kind == "batch" and not inhibit.is_set():
                if not state.command(token, timestamp, time.monotonic(), *payload):
                    report("paused", "Input command rejected; explicitly activate again")
    except Exception as e:
        inhibit.set()
        report("error", str(e))
    finally:
        # A failed release stays owned. Keep the non-daemon worker alive to retry
        # cleanup while the UI keeps closing pending, rather than terminating it.
        while executor and executor.held:
            try:
                executor.release_all()
            except Exception as e:
                inhibit.set()
                report("error", str(e))
                time.sleep(0.1)
        release_complete.set()
        if listener:
            listener.stop()


class InputSupervisor:
    def __init__(self):
        ctx = mp.get_context("spawn")
        self.commands = ctx.Queue(maxsize=8)
        self.status = ctx.Queue(maxsize=32)
        self.inhibit, self.stop = ctx.Event(), ctx.Event()
        self.epoch = ctx.Value("Q", 0)
        self.release_complete = ctx.Event()
        self.inhibit.set()
        self.process = ctx.Process(target=_worker, args=(self.commands, self.status, self.inhibit, self.stop, self.epoch, self.release_complete),
                                   name="MouseInputWatchdog", daemon=False)
        self.process.start()
        self.token = None
        self.ready = False
        self.emergency_verified = False
        self.screens = []

    def poll(self):
        events = []
        while True:
            try:
                kind, detail = self.status.get_nowait()
            except Empty:
                break
            if kind == "ready":
                self.ready = True
            if kind == "monitors":
                self.screens = [Monitor(**m) for m in detail]
            if kind == "error":
                self.ready = False
            if kind == "stop":
                self.emergency_verified = True
            if kind in ("stop", "error", "paused"):
                self.pause()
            events.append((kind, detail))
        if not self.process.is_alive():
            self.ready = False
            self.pause()
        return events

    def activate(self):
        if not self.ready or not self.emergency_verified or not self.process.is_alive():
            raise RuntimeError("Authorize/verify input and physically test the global stop before activation")
        self.pause()
        self.token = self.epoch.value
        self.activated_at = time.monotonic()
        self.inhibit.clear()
        self._put(("arm", self.token, self.activated_at, None))

    def _put(self, message):
        try:
            self.commands.put_nowait(message)
        except Full:
            self.pause()
            raise RuntimeError("Input queue congested; paused")

    def publish(self, timestamp, actions, xy, scroll):
        if (self.token is not None and not self.inhibit.is_set()
                and timestamp > self.activated_at):
            self._put(("batch", self.token, timestamp, (actions, xy, scroll)))

    def pause(self):
        self.inhibit.set()
        with self.epoch.get_lock():
            self.epoch.value += 1
        self.token = None

    def close(self):
        self.pause()
        self.stop.set()
        self.process.join(timeout=2)
        if self.process.is_alive():
            # Do not forcibly kill the process that might still be releasing app-held input.
            return False
        return self.release_complete.is_set()


def _probe_recording_child(connection):
    from .platforms import RecordingAdapter
    adapter = RecordingAdapter()
    state = WorkerState(Executor(adapter))
    state.arm("probe", 10.)
    state.command("probe", 10.1, 10.1, ["drag"], None, 3)
    state.tick(10.5, False)
    connection.send({"native_input": False, "owned_buttons_released": not adapter.held,
                     "events": adapter.events, "evidence": "Spawned recording adapter; not physical input"})
    connection.close()


def probe_recording_worker():
    ctx = mp.get_context("spawn")
    receiver, sender = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_probe_recording_child, args=(sender,))
    process.start()
    sender.close()
    try:
        if not receiver.poll(10):
            raise RuntimeError("Recording worker spawn probe timed out")
        result = receiver.recv()
    finally:
        receiver.close()
        process.join(timeout=2)
        if process.is_alive():
            process.terminate()  # This probe owns only a recording adapter, no real input.
            process.join(timeout=2)
    if process.exitcode != 0:
        raise RuntimeError(f"Recording worker failed: {process.exitcode}")
    return result
