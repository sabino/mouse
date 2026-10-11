"""Action policy shared by live control and event-level evaluation."""
from dataclasses import dataclass, field
import math

ACTIONS = ("none", "pointer", "click", "secondary", "drag", "release", "scroll_up", "scroll_down")
DEFAULT_MAPPING = {"neutral": "none", "confusing": "none", **{k: k for k in ACTIONS if k != "none"}}


@dataclass
class Policy:
    mapping: dict = field(default_factory=lambda: DEFAULT_MAPPING.copy())
    dwell: float = 0.15
    neutral_dwell: float = 0.20
    armed: bool = False
    candidate: str = ""
    since: float = 0.
    last_time: float = -1.
    holding: bool = False

    def reset(self):
        self.armed = self.holding = False
        self.candidate = ""
        self.since = 0.
        self.last_time = -1.

    def step(self, label, timestamp):
        if not math.isfinite(timestamp) or timestamp <= self.last_time:
            self.reset()
            return ["release"]
        self.last_time = timestamp
        if label in ("rejected", "confusing", "lost"):
            self.armed = False
            self.candidate = ""
            if self.holding:
                self.holding = False
                return ["release"]
            return []
        if label != self.candidate:
            self.candidate, self.since = label, timestamp
            return []
        elapsed = timestamp - self.since
        if label == "neutral":
            if elapsed >= self.neutral_dwell:
                self.armed = True
                if self.holding:
                    self.holding = False
                    return ["release"]
            return []
        if elapsed < self.dwell:
            return []
        action = self.mapping.get(label, "none")
        if action == "release":
            if self.holding:
                self.holding, self.armed = False, False
                return ["release"]
            return []
        if action == "pointer":
            return ["pointer"] if self.armed or self.holding else []
        if action == "drag" and self.holding:
            return ["pointer"]
        if action in ("click", "secondary", "drag", "scroll_up", "scroll_down") and self.armed:
            self.armed = False
            if action == "drag":
                self.holding = True
            return [action]
        return []
