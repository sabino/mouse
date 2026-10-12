"""Temporal pose + motion features, independent of any action geometry rules."""
from dataclasses import dataclass
import numpy as np

FEATURE_SCHEMA = "hand-temporal-v1"
WINDOW_SECONDS = 0.6
MIN_SPAN = 0.48
MAX_GAP = 0.20
SAMPLE_COUNT = 5
JOINTS = [(a, a+1, a+2) for a in (1, 5, 9, 13, 17)] + [
    (0, a, a+1) for a in (1, 5, 9, 13, 17)]
SPATIAL_DIM = 63 + len(JOINTS) + 5
FEATURE_DIM = SPATIAL_DIM * SAMPLE_COUNT + 9


@dataclass
class Frame:
    timestamp: float
    points: np.ndarray
    hand: str = "Right"

    def __post_init__(self):
        self.points = np.asarray(self.points, dtype=float)
        if (self.points.shape != (21, 3) or not np.isfinite(self.points).all()
                or np.abs(self.points).max() > 10 or not np.isfinite(self.timestamp)
                or self.timestamp < 0 or self.hand not in ("Left", "Right")):
            raise ValueError("Invalid landmark frame")

    def to_dict(self):
        self.__post_init__()  # Mutable frames must remain loadable when exported.
        return {"timestamp": self.timestamp, "points": self.points.tolist(), "hand": self.hand}

    @classmethod
    def from_dict(cls, d):
        return cls(d["timestamp"], d["points"], d["hand"])


def spatial(frame):
    p = frame.points.copy()
    p -= p[0]
    scale = np.linalg.norm(p[9])
    if scale < 1e-5:
        raise ValueError("Degenerate palm landmarks")
    p /= scale
    if frame.hand == "Left":
        p[:, 0] *= -1
    angles = []
    for a, b, c in JOINTS:
        u, v = p[a] - p[b], p[c] - p[b]
        angles.append(np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-8))
    distances = [np.linalg.norm(p[i] - p[4]) for i in (8, 12, 16, 20, 0)]
    return np.r_[p.ravel(), angles, distances]


def extract(frames):
    """Interpolate by real elapsed time; reject gaps, hand switches and short windows."""
    if len(frames) < 5:
        raise ValueError("Need at least five tracked frames")
    times = np.array([f.timestamp for f in frames])
    elapsed = times[-1] - times[0]
    if (elapsed < MIN_SPAN or elapsed > WINDOW_SECONDS + 0.08
            or np.any(np.diff(times) <= 0) or np.max(np.diff(times)) > MAX_GAP
            or len({f.hand for f in frames}) != 1):
        raise ValueError("Invalid temporal window: duration, gap or hand changed")
    poses = np.stack([spatial(f) for f in frames])
    grid = np.linspace(times[0], times[-1], SAMPLE_COUNT)
    sampled = np.stack([np.interp(grid, times, poses[:, i]) for i in range(SPATIAL_DIM)], axis=1)
    wrists = np.stack([f.points[0] for f in frames])
    delta = wrists[-1] - wrists[0]
    velocity = np.diff(wrists, axis=0) / np.diff(times)[:, None]
    return np.r_[sampled.ravel(), delta, velocity.mean(axis=0), velocity.std(axis=0)]


def windows(frames, stride=0.10):
    start, last = 0, -float("inf")
    for end, frame in enumerate(frames):
        while start < end and frame.timestamp - frames[start].timestamp > WINDOW_SECONDS:
            start += 1
        if frame.timestamp - last < stride:
            continue
        try:
            feature = extract(frames[start:end+1])
        except ValueError:
            continue
        last = frame.timestamp
        yield frame.timestamp, feature
