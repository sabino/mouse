"""Verify downloaded native bytes/provenance and Unix launcher permissions, no input."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import zipfile

folder = Path(sys.argv[1]).resolve()
index = json.loads((folder / "artifact-index.json").read_text(encoding="utf-8"))
name = index["archive"]
if Path(name).name != name:
    raise ValueError("Invalid archive filename")
archive = folder / name
with archive.open("rb") as f:
    digest = hashlib.file_digest(f, "sha256").hexdigest()
assert digest == index["sha256"] and archive.stat().st_size == index["archive_bytes"]
if name.endswith(".tar.gz"):
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        manifest = json.load(tar.extractfile("BUILD-INFO.json"))
        names = [m.name for m in members]
        launcher = tar.getmember(index["launcher"])
        assert launcher.isfile() and launcher.mode & 0o111, "Unix launcher lost executable permission"
        assert tar.getmember("dependency-licenses.json").isfile()
else:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        manifest = json.loads(z.read("BUILD-INFO.json"))
        assert index["launcher"] in names and "dependency-licenses.json" in names
for name in names:
    path = PurePosixPath(name)
    assert not path.is_absolute() and ".." not in path.parts
    assert path.suffix.lower() not in (".task", ".tflite"), "Unexpected model asset"
assert manifest["source_sha"] == index["source_sha"]
assert manifest["pr_head_sha"] == index["pr_head_sha"]
assert manifest["hardware_tested"] is False and manifest["weights_bundled"] is False
print(json.dumps({"verified": True, "source_sha": index["source_sha"], "platform": index["platform"],
                  "sha256": digest, "archive_bytes": archive.stat().st_size, "native_input": False}))
