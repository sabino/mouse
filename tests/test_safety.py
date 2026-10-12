from mouse_invisivel.safety import Policy


def neutral(policy, t=0.):
    policy.step("neutral", t)
    policy.step("neutral", t + .25)


def test_neutral_rearm_once_and_rejection():
    p = Policy()
    assert p.step("click", 0) == []
    assert p.step("click", .2) == []
    neutral(p, .3)
    assert p.step("click", .6) == []
    assert p.step("click", .8) == ["click"]
    assert p.step("click", 1.) == []
    assert p.step("rejected", 1.1) == []
    assert p.step("click", 1.2) == []
    assert p.step("click", 1.4) == []
    neutral(p, 1.5)
    p.step("click", 1.8)
    assert p.step("click", 2.) == ["click"]


def test_tracking_loss_release_and_no_rearm():
    p = Policy()
    neutral(p)
    p.step("drag", .3)
    assert p.step("drag", .5) == ["drag"]
    assert p.step("drag", .7) == ["pointer"]
    assert p.step("lost", .8) == ["release"]
    assert not p.holding and not p.armed
    assert p.step("drag", .9) == []
    assert p.step("drag", 1.1) == []


def test_explicit_release_and_bad_clock():
    p = Policy()
    neutral(p)
    p.step("drag", .3)
    p.step("drag", .5)
    p.step("release", .6)
    assert p.step("release", .8) == ["release"]
    assert p.step("click", .7) == ["release"]


def test_worker_watchdog_pause_stale_and_generation():
    from mouse_invisivel.input_worker import WorkerState, Executor
    from mouse_invisivel.platforms import RecordingAdapter
    adapter = RecordingAdapter()
    state = WorkerState(Executor(adapter))
    state.arm("new", 10.)
    assert not state.command("old", 10.1, 10.1, ["drag"], (10, 20), 3)
    assert not adapter.held
    assert state.command("new", 10.1, 10.12, ["drag"], (10, 20), 3)
    assert adapter.held == {"left"}
    assert state.tick(10.5, False)
    assert not adapter.held and state.token is None
    state.arm("next", 11.)
    state.command("next", 11.1, 11.1, ["drag"], None, 3)
    assert state.tick(11.12, True)
    assert not adapter.held
    state.arm("stale", 12.)
    assert not state.command("stale", 12.1, 12.5, ["drag"], None, 3)
    assert not adapter.held


def test_only_owned_buttons_released_on_native_error():
    from mouse_invisivel.input_worker import Executor
    from mouse_invisivel.platforms import RecordingAdapter
    import pytest
    class PartialFailure(RecordingAdapter):
        def press(self, button):
            super().press(button)
            raise RuntimeError("native operation failed after press")
    a = PartialFailure()
    e = Executor(a)
    with pytest.raises(RuntimeError):
        e.execute(["click"], None, 3)
    e.release_all()
    assert a.events == [("press", "left"), ("release", "left")]


def test_wayland_explicitly_denied(monkeypatch):
    from mouse_invisivel.platforms import input_allowed
    import sys
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert not input_allowed()[0]


def test_bounded_uncertain_transition_never_executes_and_eventually_disarms():
    p = Policy()
    neutral(p)
    assert p.step("rejected", .3) == []
    assert p.armed
    p.step("click", .5)
    assert p.step("click", .7) == ["click"]
    neutral(p, .8)
    assert p.step("rejected", 1.1) == []
    assert p.step("rejected", 1.9) == []
    assert not p.armed
    p.step("click", 2.)
    assert p.step("click", 2.2) == []
