"""Synthetic unit fixtures ONLY. These are not training assets or real-world evidence."""
import numpy as np
import pytest
from mouse_invisivel.features import Frame, extract, FEATURE_DIM
from mouse_invisivel.dataset import Session, Clip
from mouse_invisivel.model import Model, train
from mouse_invisivel.calibration import Calibration
from mouse_invisivel.profile import Profile
from mouse_invisivel.storage import write_json


def fake_points(label, offset=0.):
    # Mathematical fixture deliberately distinguishable, not a physical hand dataset.
    p = np.arange(63).reshape(21, 3) / 100 + offset
    if label == "click":
        p[8] += [0.2, -0.1, 0.05]
    if label == "confusing":
        p[12] += [-0.12, 0.15, 0.07]
    return p


def fixture_session(sid):
    clips = []
    for i, label in enumerate(["neutral", "click", "neutral", "confusing", "neutral", "click"]):
        clips.append(Clip(label, [Frame(i * 3.05 + j / 30, fake_points(label, int(sid[-1]) / 1000))
                                  for j in range(90)]))
    return Session("test-person", id=sid, source="synthetic-test", clips=clips)


def test_temporal_feature_and_loss():
    frames = fixture_session("s1").clips[0].frames[:19]
    assert extract(frames).shape == (FEATURE_DIM,)
    with pytest.raises(ValueError):
        extract(frames[:3])
    frames[8].timestamp += .3
    with pytest.raises(ValueError):
        extract(frames)


def test_train_save_reload_and_split(tmp_path):
    sessions = [fixture_session("s1"), fixture_session("s2")]
    for s in sessions:
        s.save(tmp_path / f"{s.id}.json")
    loaded = [Session.load(tmp_path / f"{s.id}.json") for s in sessions]
    model = train(loaded, ["s2"])
    assert model.report["train_sessions"] == ["s1"]
    assert model.report["holdout_sessions"] == ["s2"]
    assert "synthetic" in model.report["evidence"]
    from mouse_invisivel.features import windows
    feature = list(windows(loaded[1].clips[1].frames))[0][1]
    model.save(tmp_path / "model.json")
    restored = Model.load(tmp_path / "model.json")
    np.testing.assert_allclose(restored.probabilities(feature), model.probabilities(feature))
    assert restored.predict(feature)[0] == "click"
    from sklearn.linear_model import LogisticRegression
    from mouse_invisivel.model import materialize
    x, y = materialize([loaded[0]])
    estimator = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=7).fit(
        (x-model.mean)/model.scale, y)
    np.testing.assert_allclose(restored.probabilities(feature), estimator.predict_proba(
        ((feature-model.mean)/model.scale)[None])[0])
    nb = train(loaded, ["s2"], kind="gaussian_nb")
    nb.save(tmp_path / "nb.json")
    np.testing.assert_allclose(Model.load(tmp_path / "nb.json").probabilities(feature), nb.probabilities(feature))


def test_refuse_invalid_splits_and_missing_negatives():
    with pytest.raises(ValueError):
        train([fixture_session("s1")], ["s1"])
    with pytest.raises(ValueError):
        train([fixture_session("s1"), fixture_session("s1")], ["s1"])
    sessions = [fixture_session("s1"), fixture_session("s2")]
    sessions[0].clips = [c for c in sessions[0].clips if c.label != "confusing"]
    with pytest.raises(ValueError):
        train(sessions, ["s2"])
    with pytest.raises(ValueError):
        train([fixture_session("s1"), fixture_session("s2")], ["test-person"], by_person=True)


def test_unsafe_model_and_nonfinite_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"schema":"pickle","__reduce__":"execute"}')
    with pytest.raises(ValueError):
        Model.load(p)
    p.write_text('{"number":NaN}')
    with pytest.raises(ValueError):
        Model.load(p)
    model = train([fixture_session("s1"), fixture_session("s2")], ["s2"])
    model.scale[0] = 0
    model.save(p)
    with pytest.raises(ValueError):
        Model.load(p)


def test_separate_pointer_regression_and_profile(tmp_path):
    points = [[.2, .2], [.8, .2], [.5, .5], [.2, .8], [.8, .8]]
    calibration = Calibration.fit(points, [[0, 0], [1, 0], [.5, .5], [0, 1], [1, 1]])
    np.testing.assert_allclose(calibration.predict([.5, .5]), [.5, .5], atol=.001)
    profile = Profile(calibration=calibration)
    profile.save(tmp_path / "profile.json")
    assert Profile.load(tmp_path / "profile.json").calibration is not None
    d = {"schema": "bad"}
    write_json(tmp_path / "profile.json", d)
    with pytest.raises(ValueError):
        Profile.load(tmp_path / "profile.json")
    with pytest.raises(ValueError):
        Calibration.fit([[.2, .2]] * 5, points)
