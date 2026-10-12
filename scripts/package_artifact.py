"""Create a native archive with permissions, source provenance and checksums intact."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import zipfile

root = Path(__file__).resolve().parents[1]
target = "macOS" if sys.platform == "darwin" else "Windows" if sys.platform == "win32" else "Linux"
app = root / "dist" / ("MouseInvisivel.app" if target == "macOS" else "MouseInvisivel")
launcher = (app / "Contents" / "MacOS" / "MouseInvisivel" if target == "macOS"
            else app / ("MouseInvisivel.exe" if target == "Windows" else "MouseInvisivel"))
if not launcher.is_file() or (target != "Windows" and not os.access(launcher, os.X_OK)):
    raise RuntimeError("Native launcher missing or not executable")
if any(p.suffix.lower() in (".task", ".tflite") for p in app.rglob("*")):
    raise RuntimeError("Unexpected model weights in native build; do not upload")
license_file = root / "dist" / "dependency-licenses.json"
if not license_file.is_file():
    raise RuntimeError("Dependency license inventory missing")
source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=root, check=True)
if json.loads((root / "dist" / "build-source.json").read_text())["source_sha"] != source:
    raise RuntimeError("Native build does not belong to the current clean source commit")
manifest = {"schema": "native-artifact-v1", "source_sha": source,
            "pr_head_sha": os.environ.get("MOUSE_SOURCE_HEAD_SHA", source),
            "platform": target, "architecture": platform.machine(),
            "launcher": launcher.relative_to(root / "dist").as_posix(),
            "hardware_tested": False, "weights_bundled": False,
            "validation": "Native build and headless/synthetic/protocol checks; see associated CI run",
            "distribution_review": "Draft engineering artifact; final license/signing acceptance remains open"}
out = root / "artifacts"
out.mkdir(exist_ok=True)
manifest_file = out / "BUILD-INFO.json"
manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
name = f"MouseInvisivel-{target}-{platform.machine()}-{source[:12]}"
archive = out / (name + (".zip" if target == "Windows" else ".tar.gz"))
if target == "Windows":
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(app.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(root / "dist").as_posix())
        z.write(license_file, "dependency-licenses.json")
        z.write(manifest_file, "BUILD-INFO.json")
else:
    # GitHub's artifact ZIP does not preserve executable bits/symlinks. A tar
    # inside that ZIP preserves native app/framework semantics after download.
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(app, arcname=app.name)
        tar.add(license_file, arcname="dependency-licenses.json")
        tar.add(manifest_file, arcname="BUILD-INFO.json")
with archive.open("rb") as f:
    digest = hashlib.file_digest(f, "sha256").hexdigest()
index = {**manifest, "archive": archive.name, "archive_bytes": archive.stat().st_size, "sha256": digest}
(out / "artifact-index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
(out / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
print(json.dumps(index))
