from mouse_invisivel.runtime import Runtime
from mouse_invisivel.profile import Profile
from mouse_invisivel.features import Frame
from test_learning import fake_points
import pytest


class FakeModel:
    def __init__(self):
        self.label = "neutral"
    def predict(self, _x, _threshold, _margin):
        return self.label, .99


def test_replay_bridge_staleness_loss_and_reset():
    model = FakeModel()
    runtime = Runtime(Profile(), model)
    for n in range(31):
        t = 10 + n / 30
        runtime.process(Frame(t, fake_points("neutral")), now=t+.01)
    assert runtime.policy.armed
    model.label = "drag"
    emitted = []
    for n in range(31, 43):
        t = 10 + n/30
        emitted.extend(runtime.process(Frame(t, fake_points("click")), now=t+.01)[2])
    assert "drag" in emitted
    result = runtime.process(Frame(11.5, fake_points("click")), now=12.)
    assert result[0] == "lost" and result[2] == ["release"]
    assert not runtime.policy.holding
    assert runtime.process(None)[2] == ["release"]


def test_preview_has_no_native_side_effects():
    runtime = Runtime(Profile(), FakeModel())
    assert runtime.process(Frame(1., fake_points("neutral")), now=1.01)[0] == "warming"
    assert not hasattr(runtime, "adapter")


def drag_runtime():
    from mouse_invisivel.input_worker import Executor
    from mouse_invisivel.platforms import RecordingAdapter
    model = FakeModel()
    runtime = Runtime(Profile(), model)
    adapter = RecordingAdapter()
    executor = Executor(adapter)
    for n in range(31):
        t = 10 + n / 30
        result = runtime.process(Frame(t, fake_points("neutral")), now=t+.01)
        executor.execute(result[2], None, 3)
    model.label = "drag"
    for n in range(31, 43):
        t = 10 + n / 30
        result = runtime.process(Frame(t, fake_points("click")), now=t+.01)
        executor.execute(result[2], None, 3)
    assert adapter.held == {"left"}
    return runtime, adapter, executor


def test_degenerate_fresh_landmarks_release_drag_and_disarm():
    import numpy as np
    runtime, adapter, executor = drag_runtime()
    t = 10 + 43/30
    result = runtime.process(Frame(t, np.zeros((21, 3))), now=t+.01)
    executor.execute(result[2], None, 3)
    assert not adapter.held, "Fresh invalid features must release; empty heartbeats cannot retain a drag"
    assert result[0] == "lost" and result[2] == ["release"]
    assert not runtime.policy.holding and not runtime.policy.armed
    assert not runtime.frames


def test_hand_switch_release_drag_and_disarm():
    runtime, adapter, executor = drag_runtime()
    t = 10 + 43/30
    result = runtime.process(Frame(t, fake_points("click"), hand="Left"), now=t+.01)
    executor.execute(result[2], None, 3)
    assert not adapter.held, "Resetting policy on a hand switch must also release native ownership"
    assert result[0] == "lost" and result[2] == ["release"]
    assert not runtime.policy.holding and not runtime.policy.armed


@pytest.mark.parametrize("discontinuity", ["gap", "out_of_order"])
def test_saved_replay_releases_drag_at_frame_discontinuity(discontinuity):
    from mouse_invisivel.replay import replay_session
    from mouse_invisivel.dataset import Session, Clip
    from mouse_invisivel.input_worker import Executor
    from mouse_invisivel.platforms import RecordingAdapter
    class ScriptedModel:
        def __init__(self):
            self.predictions = 0
        def predict(self, *_):
            self.predictions += 1
            return ("neutral" if self.predictions <= 16 else "drag"), .99
    frames = [Frame(10+n/30, fake_points("neutral")) for n in range(50)]
    last = frames[-1].timestamp
    next_start = last+1 if discontinuity == "gap" else last-.5
    session = Session("test", source="synthetic-test", clips=[Clip("neutral", frames),
        Clip("drag", [Frame(next_start+n/30, fake_points("click")) for n in range(5)])])
    result = replay_session(session, ScriptedModel())
    adapter = RecordingAdapter()
    executor = Executor(adapter)
    for event in result["events"]:
        executor.execute(event["actions"], None, 3)
    assert any("drag" in e["actions"] for e in result["events"])
    assert not adapter.held, "Replay must include the same discontinuity release as live Runtime"
    assert any(e["timestamp"] == next_start and e["actions"] == ["release"] for e in result["events"])
