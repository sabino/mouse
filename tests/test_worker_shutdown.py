"""Production supervisor/worker shutdown with recording input, no native devices."""
from functools import partial
import multiprocessing as mp
import sys
import time
from types import SimpleNamespace


def recording_worker(*args, events, allow_release):
    from mouse_invisivel import input_worker
    from mouse_invisivel.platforms import RecordingAdapter, Monitor
    class RetryAdapter(RecordingAdapter):
        attempts = 0
        def press(self, button):
            super().press(button)
            events.put(("pressed", button))
        def release(self, button):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("Recording-only temporary release failure")
            if not allow_release.wait(10):
                raise RuntimeError("Recording release gate timeout")
            super().release(button)
            events.put(("released", button))
    class Listener:
        def __init__(self, **_):
            self.alive = True
        def start(self):
            pass
        def wait(self):
            pass
        def is_alive(self):
            return self.alive
        def stop(self):
            self.alive = False
    input_worker.make_adapter = RetryAdapter
    input_worker.monitors = lambda: [Monitor("recording", 0, 0, 100, 100)]
    sys.modules["pynput"] = SimpleNamespace(keyboard=SimpleNamespace(
        Listener=Listener, Key=SimpleNamespace(esc="escape")))
    input_worker._worker(*args)


def test_production_worker_retries_release_before_close_ack(monkeypatch):
    from mouse_invisivel import input_worker
    ctx = mp.get_context("spawn")
    events, allow_release = ctx.Queue(), ctx.Event()
    monkeypatch.setattr(input_worker, "_worker", partial(recording_worker, events=events, allow_release=allow_release))
    supervisor = input_worker.InputSupervisor()
    try:
        assert supervisor.process.daemon is False
        deadline = time.monotonic()+5
        while not supervisor.ready and time.monotonic() < deadline:
            supervisor.poll()
            time.sleep(.01)
        assert supervisor.ready
        supervisor.emergency_verified = True  # Recording listener only; not physical stop evidence.
        supervisor.activate()
        time.sleep(.03)
        supervisor.publish(time.monotonic(), ["drag"], None, 3)
        assert events.get(timeout=5) == ("pressed", "left")
        assert not supervisor.close()
        assert supervisor.process.is_alive() and not supervisor.release_complete.is_set()
        allow_release.set()
        assert events.get(timeout=5) == ("released", "left")
        supervisor.process.join(5)
        assert supervisor.close() and supervisor.release_complete.is_set()
    finally:
        allow_release.set()
        supervisor.stop.set()
        supervisor.process.join(5)
