"""Replay saved landmark sessions through inference/policy with zero native input."""
from .runtime import Runtime
from .profile import Profile


def replay_session(session, model, profile=None):
    runtime = Runtime(profile or Profile(), model)
    events = []
    last = None
    for clip in session.clips:
        for frame in clip.frames:
            if last is not None and (frame.timestamp <= last or frame.timestamp - last > .2):
                runtime.reset()
            label, confidence, actions, uv = runtime.process(frame, now=frame.timestamp)
            if actions:
                events.append({"timestamp": frame.timestamp, "ground_truth_clip": clip.label,
                               "predicted": label, "confidence": confidence, "actions": actions,
                               "pointer_uv": uv.tolist() if uv is not None else None})
            last = frame.timestamp
    return {"schema": "safe-replay-v1", "session": session.id, "source": session.source,
            "native_input": False, "events": events,
            "evidence": "Saved landmarks only; camera capture and physical input are not tested by replay."}
