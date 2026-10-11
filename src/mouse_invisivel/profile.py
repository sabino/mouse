from dataclasses import dataclass, field, asdict
from .calibration import Calibration
from .safety import DEFAULT_MAPPING, ACTIONS
from .dataset import label_valid
from .storage import read_json, write_json, number

PROFILE_SCHEMA = "mapping-profile-v1"


@dataclass
class Profile:
    name: str = "Meu perfil"
    hand: str = "Right"
    camera: int = 0
    monitor: int = 0
    sensitivity: float = 1.
    smoothing: float = 0.08
    confidence: float = 0.80
    margin: float = 0.15
    dwell: float = 0.15
    scroll_step: int = 3
    mapping: dict = field(default_factory=lambda: DEFAULT_MAPPING.copy())
    calibration: Calibration | None = None

    def save(self, path):
        d = asdict(self)
        d["schema"] = PROFILE_SCHEMA
        d["calibration"] = self.calibration.to_dict() if self.calibration else None
        write_json(path, d)

    @classmethod
    def load(cls, path):
        d = read_json(path)
        if (d.get("schema") != PROFILE_SCHEMA or d.get("hand") not in ("Left", "Right")
                or not isinstance(d.get("name"), str) or not 1 <= len(d["name"]) <= 128):
            raise ValueError("Invalid profile schema")
        mapping = d.get("mapping")
        if (not isinstance(mapping, dict) or len(mapping) > 32 or not all(label_valid(k) for k in mapping)
                or not all(a in ACTIONS for a in mapping.values())
                or mapping.get("neutral") != "none" or mapping.get("confusing") != "none"):
            raise ValueError("Neutral/confusing must never execute input")
        values = {k: number(d[k], low, high) for k, low, high in [
            ("sensitivity", 0.1, 3.), ("smoothing", 0., 1.), ("confidence", 0.5, 1.),
            ("margin", 0., 1.), ("dwell", 0.05, 1.)]}
        for k, high in [("camera", 32), ("monitor", 32), ("scroll_step", 20)]:
            n = number(d[k], 0 if k != "scroll_step" else 1, high)
            if int(n) != n:
                raise ValueError("Expected integer")
            values[k] = int(n)
        calibration = Calibration.from_dict(d["calibration"]) if d.get("calibration") else None
        return cls(name=d["name"], hand=d["hand"], mapping=mapping, calibration=calibration, **values)
