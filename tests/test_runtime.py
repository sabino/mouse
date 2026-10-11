from mouse_invisivel.runtime import Runtime
from mouse_invisivel.profile import Profile
from mouse_invisivel.features import Frame
from test_learning import fake_points


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
