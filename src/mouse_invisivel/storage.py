"""Bounded numeric JSON persistence; never deserialize executable Python objects."""
import json
import math
import os
from pathlib import Path
import tempfile

MAX_BYTES = 32 * 1024 * 1024


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("File exceeds the 32 MiB local schema limit")
    def reject(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    with path.open(encoding="utf-8") as f:
        value = json.load(f, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement prevents partially written profiles after interruption.
    fd, tmp = tempfile.mkstemp(prefix=".mouse-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, allow_nan=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected numeric value")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Numeric value out of schema range")
    return float(value)
