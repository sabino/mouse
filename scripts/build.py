"""Build on the target OS; unsigned local artifact, no release/upload/deployment."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "MouseInvisivel", "--paths", str(root / "src"),
        "--collect-binaries", "mediapipe", "--collect-submodules", "mediapipe.tasks.python.vision",
        "--collect-submodules", "mediapipe.framework", "--collect-submodules", "pynput",
        "--exclude-module", "jax", "--exclude-module", "jaxlib",
        "--copy-metadata", "mediapipe", "--copy-metadata", "scikit-learn",
        "--hidden-import", "sklearn.utils._cython_blas", "--hidden-import", "sklearn.utils._typedefs",
        "--hidden-import", "sklearn.neighbors._partition_nodes",
        "--add-data", f"{root / 'docs'}:docs"]
if sys.platform == "darwin":
    args += ["--windowed", "--osx-bundle-identifier", "local.mouse-invisivel.desktop"]
    # PyInstaller spec is patched below to carry an explicit camera usage explanation.
args += [str(root / "scripts" / "launcher.py")]
subprocess.run(args, cwd=root, check=True)
if sys.platform == "darwin":
    import plistlib
    plist = root / "dist" / "MouseInvisivel.app" / "Contents" / "Info.plist"
    with plist.open("rb") as f:
        info = plistlib.load(f)
    info["NSCameraUsageDescription"] = "Prévia local e landmarks para seus gestos; nenhum vídeo é gravado ou enviado."
    info["NSMicrophoneUsageDescription"] = "Mouse Invisível não usa áudio nem abre o microfone."
    with plist.open("wb") as f:
        plistlib.dump(info, f)
    # Updating Info.plist invalidates an ad-hoc signature; re-sign locally, no identity/network.
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(plist.parents[1])], check=True)
