"""Evaluate held-out labeled episodes using the same dwell/re-arm policy as runtime.

Clip labels are episode ground truth, not expert timestamp annotations. Precision,
recall and detection latency are therefore coarse personal-clip diagnostics.
"""
import numpy as np
from .features import windows
from .safety import Policy, DEFAULT_MAPPING


def evaluate_events(model, sessions, threshold, margin, dwell):
    tp = fp = fn = idle_events = 0
    idle_seconds = 0.
    latencies = []
    action_names = {"click", "secondary", "drag", "release", "scroll_up", "scroll_down"}
    for session in sessions:
        policy = Policy(dwell=dwell)
        previous_end = -1.
        for clip in session.clips:
            start, end = clip.frames[0].timestamp, clip.frames[-1].timestamp
            if start <= previous_end or start - previous_end > 0.75:
                policy.reset()
            previous_end = end
            expected = DEFAULT_MAPPING.get(clip.label, "none")
            found = False
            idle = clip.label in ("neutral", "confusing")
            if idle:
                idle_seconds += end - start
            for timestamp, feature in windows(clip.frames):
                label, _ = model.predict(feature, threshold, margin)
                for action in policy.step(label, timestamp):
                    if action not in action_names:
                        continue
                    # Safety release is not a false action episode on idle/rejected states.
                    if action == "release" and label in ("neutral", "confusing", "rejected"):
                        continue
                    if idle:
                        idle_events += 1
                    if action == expected and not found:
                        tp += 1
                        found = True
                        latencies.append(timestamp - start)
                    else:
                        fp += 1
            if expected in action_names and not found:
                fn += 1
    return {"episode_precision": tp / (tp + fp) if tp + fp else None,
            "episode_recall": tp / (tp + fn) if tp + fn else None,
            "true_positive_events": tp, "false_positive_events": fp, "missed_episodes": fn,
            "idle_minutes": idle_seconds / 60,
            "false_activations_per_idle_minute": idle_events / (idle_seconds / 60) if idle_seconds else None,
            "median_episode_latency_seconds": float(np.median(latencies)) if latencies else None,
            "note": "Clip-level labels; gaps reset arming. Record neutral then action sequences for meaningful events."}
