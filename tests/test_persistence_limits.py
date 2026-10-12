"""Schema boundary regressions; mathematical fixtures, no captured user data."""
import json
import numpy as np
import pytest
from mouse_invisivel import storage
from mouse_invisivel.dataset import Session, Clip
from mouse_invisivel.features import Frame, FEATURE_DIM
from mouse_invisivel.model import Model, train


def test_oversized_utf8_write_preserves_existing_file(tmp_path, monkeypatch):
    path = tmp_path / "session.json"
    storage.write_json(path, {"valid": "original"})
    original = path.read_bytes()
    monkeypatch.setattr(storage, "MAX_BYTES", 128)
    with pytest.raises(ValueError, match="limit|exceeds"):
        storage.write_json(path, {"large": "á" * 100})
    assert path.read_bytes() == original
    assert storage.read_json(path) == {"valid": "original"}
    assert not list(tmp_path.glob(".mouse-*"))


def test_exact_serialized_byte_boundary_round_trip(tmp_path, monkeypatch):
    value = {"label": "ação"}
    size = len(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8"))
    path = tmp_path / "boundary.json"
    monkeypatch.setattr(storage, "MAX_BYTES", size)
    storage.write_json(path, value)
    assert storage.read_json(path) == value
    monkeypatch.setattr(storage, "MAX_BYTES", size-1)
    with pytest.raises(ValueError):
        storage.write_json(path, value)


def numerical_model(classes):
    labels = ["neutral", "confusing"] + [f"gesture_{i}" for i in range(classes-2)]
    return Model("logistic", labels, np.zeros(FEATURE_DIM), np.ones(FEATURE_DIM),
                 {"coef": np.zeros((classes, FEATURE_DIM)), "intercept": np.zeros(classes)},
                 {"evidence": "synthetic-test parameters only"})


def test_model_class_limit_is_checked_before_replacing_file(tmp_path):
    path = tmp_path / "model.json"
    numerical_model(32).save(path)
    assert len(Model.load(path).labels) == 32
    original = path.read_bytes()
    with pytest.raises(ValueError, match="label|class"):
        numerical_model(33).save(path)
    assert path.read_bytes() == original


def test_training_rejects_unreloadable_class_count_before_fitting():
    points = np.arange(63).reshape(21, 3)/100
    labels = numerical_model(33).labels
    clips = [Clip(label, [Frame(i*3+j/30, points) for j in range(90)]) for i, label in enumerate(labels)]
    sessions = [Session("test", id=sid, source="synthetic-test", clips=clips) for sid in ("train", "holdout")]
    with pytest.raises(ValueError, match="label|class"):
        train(sessions, ["holdout"])


def test_session_clip_limit_round_trip_and_preservation(tmp_path):
    clip = Clip("neutral", [Frame(n/30, np.zeros((21, 3))) for n in range(5)])
    session = Session("test", source="synthetic-test", clips=[clip]*1000)
    path = tmp_path / "session.json"
    session.save(path)
    assert len(Session.load(path).clips) == 1000
    original = path.read_bytes()
    session.clips.append(clip)
    with pytest.raises(ValueError, match="clip|session"):
        session.save(path)
    assert path.read_bytes() == original


def test_gaussian_constant_examples_still_save_reload_finite_model(tmp_path):
    points = np.arange(63).reshape(21, 3)/100
    labels = ["neutral", "confusing", "click"]
    clips = [Clip(label, [Frame(i*3+j/30, points) for j in range(90)]) for i, label in enumerate(labels)]
    sessions = [Session("test", id=sid, source="synthetic-test", clips=clips) for sid in ("train", "holdout")]
    model = train(sessions, ["holdout"], kind="gaussian_nb")
    path = tmp_path / "constant.json"
    model.save(path)
    restored = Model.load(path)
    probabilities = restored.probabilities(np.zeros(FEATURE_DIM))
    assert np.isfinite(probabilities).all() and probabilities.sum() == pytest.approx(1)


def test_profile_mapping_limit_preserves_existing_profile(tmp_path):
    from mouse_invisivel.profile import Profile
    path = tmp_path / "profile.json"
    profile = Profile(mapping={label: "none" for label in numerical_model(32).labels})
    profile.save(path)
    assert len(Profile.load(path).mapping) == 32
    original = path.read_bytes()
    profile.mapping["too_many"] = "none"
    with pytest.raises(ValueError, match="mapping|label|profile"):
        profile.save(path)
    assert path.read_bytes() == original
