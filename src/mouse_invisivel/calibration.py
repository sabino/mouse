"""Continuous index-tip to screen regression; never selects a discrete gesture."""
from dataclasses import dataclass
import numpy as np

CALIBRATION_SCHEMA = "pointer-ridge-v1"


@dataclass
class Calibration:
    coef: np.ndarray
    error: float = 0.

    @classmethod
    def fit(cls, points, targets):
        x, y = np.asarray(points, dtype=float), np.asarray(targets, dtype=float)
        if (x.ndim != 2 or x.shape[1] != 2 or y.shape != x.shape or len(x) < 5
                or not np.isfinite(x).all() or not np.isfinite(y).all()
                or np.any((y < 0) | (y > 1))):
            raise ValueError("Capture five or more well-spaced calibration targets")
        design = np.c_[x, np.ones(len(x))]
        if np.linalg.matrix_rank(design) < 3 or np.linalg.cond(design) > 1000:
            raise ValueError("Calibration points are too close/collinear; move across the camera area")
        penalty = np.diag([1e-5, 1e-5, 0])
        coef = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        error = float(np.sqrt(np.mean((design @ coef - y)**2)))
        return cls(coef, error)

    def predict(self, point, sensitivity=1.):
        uv = np.r_[point, 1.] @ self.coef
        return np.clip((uv - 0.5) * sensitivity + 0.5, 0, 1)

    def to_dict(self):
        return {"schema": CALIBRATION_SCHEMA, "coef": self.coef.tolist(), "training_rmse": self.error}

    @classmethod
    def from_dict(cls, d):
        coef = np.asarray(d["coef"], dtype=float)
        if (d.get("schema") != CALIBRATION_SCHEMA or coef.shape != (3, 2)
                or not np.isfinite(coef).all() or np.abs(coef).max() > 1e4):
            raise ValueError("Invalid calibration schema")
        return cls(coef, float(d.get("training_rmse", 0.)))


class Smoother:
    def __init__(self):
        self.point, self.last = None, None

    def reset(self):
        self.point, self.last = None, None

    def update(self, point, timestamp, tau):
        p = np.asarray(point, dtype=float)
        if self.point is None or timestamp - self.last > 0.25:
            self.point = p
        else:
            dt = max(timestamp - self.last, 0.001)
            alpha = 1 - np.exp(-dt / max(tau, 0.001))
            self.point += alpha * (p - self.point)
        self.last = timestamp
        return self.point.copy()
