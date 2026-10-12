"""Bounded numeric JSON persistence; never deserialize executable Python objects."""
import json
import math
import os
from pathlib import Path
import tempfile

MAX_BYTES = 32 * 1024 * 1024


def read_json(path):
    path = Path(path)
    with path.open("rb") as f:
        encoded = f.read(MAX_BYTES + 1)
    if len(encoded) > MAX_BYTES:
        raise ValueError("File exceeds the 32 MiB local schema limit")
    def reject(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            reject(value)
        return number
    value = json.loads(encoded, parse_constant=reject, parse_float=finite_float)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def write_json(path, value):
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement prevents partially written profiles after interruption.
    fd, tmp = tempfile.mkstemp(prefix=".mouse-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            size = 0
            for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False, indent=2).iterencode(value):
                encoded = chunk.encode("utf-8")
                size += len(encoded)
                if size > MAX_BYTES:
                    raise ValueError("JSON exceeds the 32 MiB local schema limit; split/export a smaller session")
                f.write(encoded)
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
