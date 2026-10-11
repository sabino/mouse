"""Exercise frozen training/reload/replay using synthetic tests, with no devices/input."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "tests"))
from test_learning import fixture_session  # noqa: E402 - Explicitly synthetic unit data, never shipped in app artifacts.

binary = str(Path(sys.argv[1]).resolve())
probe = subprocess.run([binary, "--check-worker"], text=True, capture_output=True, check=True, timeout=30)
assert json.loads(probe.stdout)["native_input"] is False
assert json.loads(probe.stdout)["owned_buttons_released"] is True
with tempfile.TemporaryDirectory(prefix="mouse-package-test-") as folder:
    d = Path(folder)
    for sid in ("s1", "s2"):
        fixture_session(sid).save(d / f"{sid}.json")
    result = subprocess.run([binary, "--train", str(d / "s1.json"), str(d / "s2.json"),
                             "--holdout", "s2", "--output", str(d / "model.json")],
                            text=True, capture_output=True, check=True, timeout=120)
    report = json.loads(result.stdout)
    assert "synthetic-test" in report["evidence"]
    result = subprocess.run([binary, "--replay", str(d / "s2.json"), "--model", str(d / "model.json")],
                            text=True, capture_output=True, check=True, timeout=120)
    replay = json.loads(result.stdout)
    assert replay["native_input"] is False
    assert any("click" in e["actions"] for e in replay["events"])
print("Frozen capture-format -> train -> evaluate -> JSON reload -> policy replay: synthetic fixtures only.")
