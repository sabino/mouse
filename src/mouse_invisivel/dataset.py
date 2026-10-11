"""Explicit local collection of labeled clips; each session is an indivisible split unit."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from .features import Frame
from .storage import read_json, write_json

DATA_SCHEMA = "landmark-session-v1"
DEFAULT_LABELS = ("neutral", "confusing", "pointer", "click", "secondary", "drag", "release",
                  "scroll_up", "scroll_down")


def label_valid(value):
    return (isinstance(value, str) and 1 <= len(value) <= 48
            and all(c.isalnum() or c in "_-" for c in value))


@dataclass
class Clip:
    label: str
    frames: list[Frame]

    def __post_init__(self):
        if not label_valid(self.label) or not 5 <= len(self.frames) <= 18000:
            raise ValueError("Invalid label or clip size")
        if any(b.timestamp <= a.timestamp for a, b in zip(self.frames, self.frames[1:])):
            raise ValueError("Clip timestamps must increase")

    def to_dict(self):
        return {"label": self.label, "frames": [f.to_dict() for f in self.frames]}


@dataclass
class Session:
    person: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "camera"
    clips: list[Clip] = field(default_factory=list)

    def save(self, path):
        write_json(path, {"schema": DATA_SCHEMA, "id": self.id, "person": self.person,
                          "created": self.created, "source": self.source,
                          "clips": [c.to_dict() for c in self.clips]})

    @classmethod
    def load(cls, path):
        d = read_json(path)
        if (d.get("schema") != DATA_SCHEMA or not isinstance(d.get("id"), str)
                or not 1 <= len(d["id"]) <= 128 or not isinstance(d.get("person"), str)
                or not 1 <= len(d["person"]) <= 128 or d.get("source") not in ("camera", "synthetic-test")
                or not isinstance(d.get("clips"), list) or len(d["clips"]) > 1000):
            raise ValueError("Unsupported or invalid session schema")
        clips = [Clip(c["label"], [Frame.from_dict(f) for f in c["frames"]]) for c in d["clips"]]
        return cls(d["person"], d["id"], d["created"], d["source"], clips)
