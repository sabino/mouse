# Dependency and model review (2026-10-11)

The application is original. The owner made the repository public (verified 2026-10-12).
No project-wide open source license is chosen on behalf of the owner; public visibility
alone does not grant reuse rights. Third-party licenses still apply.
Native artifacts are draft CI/local artifacts, not published releases.

| Component | Pin | Upstream license / role | Delivery note |
|---|---|---|---|
| Python | 3.11/3.12 | PSF | Runtime bundled by PyInstaller |
| NumPy | 1.26.4 | BSD-3-Clause | Numeric inference |
| SciPy | 1.15.2 | BSD-3-Clause plus bundled-library notices | Ridge/ML dependencies |
| scikit-learn | 1.6.1 | BSD-3-Clause | User-trained traditional classifiers |
| PySide6 / Qt | 6.8.3 | LGPL-3.0/GPL-3.0/commercial (module-dependent) | Review exact Qt modules before distribution |
| MediaPipe code | 0.10.21 (Intel/Windows/Linux), 0.10.32 (macOS ARM) | Apache-2.0 | Pretrained neural landmark extraction runtime |
| OpenCV contrib | 4.11.0.86 | Apache-2.0 plus bundled notices | Camera access, no raw recording |
| pynput | 1.8.1 | LGPL-3.0 | Quartz/XTest adapters and Esc listener |
| platformdirs | 4.3.7 | MIT | Local data location |
| dbus-next | 0.2.3 (Linux only) | MIT | Typed session-bus portal protocol; pure Python |
| JAX / jaxlib | 0.4.35 | Apache-2.0 plus bundled notices | MediaPipe transitive; pinned for Intel/ARM platform wheels |
| PyInstaller | 6.12.0 | GPL-2.0 with bootloader exception | Native directory/app builds |

The 0.10.21 universal2 macOS wheel contains an Intel-only WHEEL tag. ARM selects
0.10.32 explicitly; CI must check its actual Tasks imports and package. We do not
suppress pip check or patch upstream wheel metadata.

`uv.lock` and `requirements-dev.lock` pin the full platform-marked graph and file hashes.
CI exports `dependency-licenses.json` and full license texts from the installed target
platform, then places them beside each artifact. This inventory is an engineering
review, not a completed distribution/legal determination. Qt LGPL requirements include
license notices, appropriate source availability and ability to replace/relink the
library. Use the directory build with shared libraries; do not represent this alone as
full compliance. Any GPL-only Qt modules accidentally collected by PyInstaller need
review/removal before public or commercial distribution. Bundled FFmpeg, BLAS and
other native library notices must also be retained/reviewed; pip metadata cannot
establish every embedded native license. Public distribution remains blocked pending
that final module/native-notice review, signing and owner approval.

Primary sources:
- https://doc.qt.io/qt-6/licensing.html
- https://www.qt.io/qt-for-python
- https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE
- https://github.com/opencv/opencv/blob/4.11.0/LICENSE
- https://github.com/scikit-learn/scikit-learn/blob/1.6.1/COPYING
- https://github.com/moses-palmer/pynput/blob/v1.8.1/COPYING.LGPL
- https://pyinstaller.org/en/stable/license.html

## Model weights: separate evidence and unresolved redistribution license

Official asset documented at:
https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker

Versioned weight URL:
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

Model card:
https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20(Lite_Full)%20with%20Fairness%20Oct%202021.pdf

On the follow-up permitted request, Python urllib reported exactly
`<urlopen error Tunnel connection failed: 403 Forbidden>` while connecting through
the environment's HTTPS proxy. There was no model HTTP response from Google Storage,
no GCS error body/asset headers and no model bytes. This is evidence of a proxy CONNECT
denial, not evidence that Google requires credentials for this documented public URL.
Acquisition stopped after that denial: no proxy bypass, alternate transport/mirror or
credentials were attempted. The official Python sample uses the same versioned URL:
https://raw.githubusercontent.com/google-ai-edge/mediapipe-samples/main/examples/hand_landmarker/python/hand_landmarker.ipynb

The model card describes a two-stage CNN. MediaPipe's code license and the website's
code-sample license are not proof of the separate weight license. This environment's
permitted request for the asset returned HTTP 403. We did not bypass that response,
download from unverified mirrors, assume a license, or bundle weights. The application
requires the user to select a licensed, locally obtained Hand Landmarker `.task` file.
Confirm that asset's terms with its provider before redistribution. A trusted file
from the official provider is preferable; native model parsers are not an arbitrary
Python deserialization path, but selecting an unknown file is not recommended.

The official sample's Apache notice covers that notebook; the documentation footer
covers page content/code samples. Neither explicitly establishes terms for the separately
hosted binary weights. Primary-source review did not resolve that distinction; do not
infer a weight license from third-party mirrors or framework metadata. A locally obtained
asset plus provider-confirmed terms remain prerequisites. `dbus-next` primary MIT source:
https://github.com/altdesktop/python-dbus-next/blob/v0.2.3/LICENSE

The personalized gesture model is numeric parameters learned from the user's own
local landmark sessions; there is no fabricated training data or bundled gesture model.
