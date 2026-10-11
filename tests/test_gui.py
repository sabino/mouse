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
