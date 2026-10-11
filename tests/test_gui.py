"""Headless GUI with synthetic landmark packets; never opens camera or native input."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from mouse_invisivel.gui import Window
from mouse_invisivel.camera import Packet
from test_learning import fake_points, fixture_session
from mouse_invisivel.features import Frame
from mouse_invisivel.model import train
from mouse_invisivel.replay import replay_session
import numpy as np
import time


def test_headless_gui_capture_label_train_reload_preview(tmp_path):
    app = QApplication.instance() or QApplication([])
    w = Window(tmp_path)
    assert not w.active and w.input is None and w.camera is None
    now = time.monotonic()
    class FakeCamera:
        def latest(self):
            return Packet(1, now, np.zeros((100, 100, 3), dtype=np.uint8),
                          Frame(now, fake_points("neutral")), "Synthetic test packet")
        def close(self):
            return True
    w.camera = FakeCamera()
    w.tick()
    assert w.last_packet.landmark is not None
    w.record_clip()
    assert w.recording["label"] == "neutral" and not w.active
    w.cancel_recording()
    sessions = [fixture_session("s1"), fixture_session("s2")]
    model = train(sessions, ["s2"])
    model.save(tmp_path / "model.json")
    from mouse_invisivel.model import Model
    w.set_model(Model.load(tmp_path / "model.json"))
    assert w.model is not None and w.input is None and not w.active
    w.confidence.setValue(.90)
    assert w.runtime.profile.confidence == .90 and not w.active
    replay = replay_session(sessions[1], model)
    assert not replay["native_input"] and replay["source"] == "synthetic-test"
    assert any("click" in e["actions"] for e in replay["events"])
    w.close()
    app.processEvents()


def test_continuous_labeled_sequence_keeps_session_boundaries_and_has_no_input(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    w = Window(tmp_path)
    w.timer.stop()
    w.session.source = "synthetic-test"
    clock = [100.]
    monkeypatch.setattr("mouse_invisivel.gui.time.monotonic", lambda: clock[0])
    state = {"seq": 0, "label": "neutral"}
    class FakeCamera:
        def latest(self):
            return Packet(state["seq"], clock[0], np.zeros((20, 20, 3), dtype=np.uint8),
                          Frame(clock[0], fake_points(state["label"])), "Synthetic unit packet")
        def close(self):
            return True
    w.camera = FakeCamera()
    w.tick()
    w.start_sequence()
    for label in ("neutral", "click", "neutral", "confusing"):
        state["label"] = label
        w.label.setCurrentText(label)
        for _ in range(60):
            clock[0] += 1/30
            state["seq"] += 1
            w.tick()
    w.end_sequence()
    assert [c.label for c in w.session.clips] == ["neutral", "click", "neutral", "confusing"]
    for a, b in zip(w.session.clips, w.session.clips[1:]):
        assert 0 < b.frames[0].timestamp-a.frames[-1].timestamp < .05
    assert not w.active and w.input is None
    w.close()
    app.processEvents()



def _delayed_recording_worker(commands, status, inhibit, stop, epoch, release_complete,
                              events, allow_release):
    import sys
    from types import SimpleNamespace
    from mouse_invisivel.platforms import RecordingAdapter, Monitor
    from mouse_invisivel import input_worker
    class DelayedAdapter(RecordingAdapter):
        def press(self, button):
            super().press(button)
            events.put(("pressed", button))
        def release(self, button):
            events.put(("release_pending", button))
            if not allow_release.wait(10):
                raise RuntimeError("Test release gate timed out")
            super().release(button)
    class FakeListener:
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
    input_worker.make_adapter = DelayedAdapter
    input_worker.monitors = lambda: [Monitor("recording-test", 0, 0, 100, 100)]
    sys.modules["pynput"] = SimpleNamespace(keyboard=SimpleNamespace(
        Listener=FakeListener, Key=SimpleNamespace(esc="escape")))
    input_worker._worker(commands, status, inhibit, stop, epoch, release_complete)


def test_close_waits_for_delayed_button_release_and_worker_completion(tmp_path):
    import multiprocessing as mp
    from mouse_invisivel.input_worker import InputSupervisor
    app = QApplication.instance() or QApplication([])
    ctx = mp.get_context("spawn")
    supervisor = InputSupervisor.__new__(InputSupervisor)
    supervisor.commands, supervisor.status = ctx.Queue(maxsize=8), ctx.Queue(maxsize=32)
    supervisor.inhibit, supervisor.stop = ctx.Event(), ctx.Event()
    supervisor.epoch, supervisor.release_complete = ctx.Value("Q", 0), ctx.Event()
    supervisor.token, supervisor.ready, supervisor.emergency_verified = None, False, True
    events, allow_release = ctx.Queue(), ctx.Event()
    supervisor.process = ctx.Process(target=_delayed_recording_worker, args=(
        supervisor.commands, supervisor.status, supervisor.inhibit, supervisor.stop,
        supervisor.epoch, supervisor.release_complete, events, allow_release), daemon=False)
    supervisor.process.start()
    deadline = time.monotonic() + 5
    while not supervisor.ready and time.monotonic() < deadline:
        supervisor.poll()
        time.sleep(.01)
    assert supervisor.ready
    supervisor.activate()
    # The real worker consumes the arm and then a fresh drag batch; only its native
    # adapter/listener are recording stubs. Production cleanup and close code run.
    time.sleep(.03)
    supervisor.publish(time.monotonic(), ["drag"], None, 3)
    assert events.get(timeout=5) == ("pressed", "left")
    w = Window(tmp_path)
    w.input = supervisor
    w.show()
    app.processEvents()
    try:
        w.close()  # The production supervisor waits 2s, then must keep the UI alive.
        assert w.isVisible(), "A timed-out release must leave closing pending; daemon shutdown cannot kill cleanup"
        assert supervisor.process.is_alive() and not supervisor.release_complete.is_set()
        assert not w.active
        allow_release.set()
        deadline = time.monotonic() + 5
        while w.isVisible() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        assert supervisor.release_complete.is_set() and not supervisor.process.is_alive()
        assert not w.isVisible()
    finally:
        allow_release.set()
        supervisor.stop.set()
        supervisor.process.join(timeout=5)
        w.input = None
        w.close()
