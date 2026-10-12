"""Inference-to-action bridge. Preview uses the same policy but never injects input."""
from collections import deque
import time
from .features import extract, WINDOW_SECONDS, MAX_GAP, MIN_SPAN
from .safety import Policy
from .calibration import Smoother
from .input_worker import MAX_AGE


class Runtime:
    def __init__(self, profile, model=None):
        self.profile, self.model = profile, model
        self.frames = deque()
        self.policy = Policy(mapping=profile.mapping.copy(), dwell=profile.dwell)
        self.smoother = Smoother()
        self.last_timestamp = None

    def reset(self):
        self.frames.clear()
        self.policy.reset()
        self.smoother.reset()
        self.last_timestamp = None

    def process(self, frame, now=None):
        now = time.monotonic() if now is None else now
        if frame is None or not 0 <= now - frame.timestamp <= MAX_AGE:
            self.reset()
            return "lost", 0., ["release"], None
        if self.last_timestamp is not None and (frame.timestamp <= self.last_timestamp
                                                or frame.timestamp - self.last_timestamp > MAX_GAP):
            self.reset()
            self.last_timestamp = frame.timestamp
            self.frames.append(frame)
            return "lost", 0., ["release"], None
        self.last_timestamp = frame.timestamp
        if self.frames and self.frames[-1].hand != frame.hand:
            self.reset()
            self.last_timestamp = frame.timestamp
            return "lost", 0., ["release"], None
        self.frames.append(frame)
        while self.frames and frame.timestamp - self.frames[0].timestamp > WINDOW_SECONDS:
            self.frames.popleft()
        if self.model is None:
            return "no-model", 0., [], None
        if len(self.frames) < 5 or self.frames[-1].timestamp - self.frames[0].timestamp < MIN_SPAN:
            # Only an initial, incomplete window is warm-up. A previously held drag
            # must never survive reduced feature coverage while fresh heartbeats continue.
            if self.policy.holding:
                self.reset()
                return "lost", 0., ["release"], None
            self.policy.reset()
            return "warming", 0., [], None
        try:
            feature = extract(list(self.frames))
        except ValueError:
            self.reset()
            return "lost", 0., ["release"], None
        label, confidence = self.model.predict(feature, self.profile.confidence, self.profile.margin)
        actions = self.policy.step(label, frame.timestamp)
        uv = None
        if self.profile.calibration and any(a in ("pointer", "drag") for a in actions):
            uv = self.profile.calibration.predict(frame.points[8, :2], self.profile.sensitivity)
            uv = self.smoother.update(uv, frame.timestamp, self.profile.smoothing)
        return label, confidence, actions, uv
