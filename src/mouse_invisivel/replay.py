"""Replay saved landmark sessions through inference/policy with zero native input."""
from .runtime import Runtime
from .profile import Profile


def replay_session(session, model, profile=None):
    runtime = Runtime(profile or Profile(), model)
    events = []
    for clip in session.clips:
        for frame in clip.frames:
            label, confidence, actions, uv = runtime.process(frame, now=frame.timestamp)
            if actions:
                events.append({"timestamp": frame.timestamp, "ground_truth_clip": clip.label,
                               "predicted": label, "confidence": confidence, "actions": actions,
                               "pointer_uv": uv.tolist() if uv is not None else None})
    return {"schema": "safe-replay-v1", "session": session.id, "source": session.source,
            "native_input": False, "events": events,
            "evidence": "Saved landmarks only; camera capture and physical input are not tested by replay."}
