# Architecture decision 001

Python 3.11/3.12, PySide6, OpenCV and MediaPipe Tasks; local JSON landmark sessions;
scikit-learn logistic regression compared with Gaussian naive Bayes. Numeric JSON
model export, no pickle/joblib/code deserialization. Temporal features preserve
normalized pose, velocity and global displacement. Sessions are split before any
windows; preprocessing sees only training sessions. Person-separated validation
is available when enough people are recorded. No bundled fabricated gesture model.

MediaPipe is a pretrained neural landmark extractor. The user gesture classifier
is a separately trained traditional statistical model. Continuous cursor control
uses its own ridge calibration regression, not gesture thresholds.

Input is gated by pause, confidence/margin rejection, neutral re-arm, dwell,
staleness and tracking health. A separate input worker watchdog owns/releases
buttons if inference or UI stops supplying heartbeats. Forced process termination,
OS failure and physical stuck buttons cannot be guaranteed by software.

Default mode: paused, local preview only, no raw recording/upload. Persistence
stores only landmarks, labels and session metadata when explicitly captured.
Linux X11, macOS accessibility and Windows normal-integrity desktops are supported
adapter targets. Native Wayland input is explicitly disabled until a consent-based
RemoteDesktop portal/libei adapter is validated. No automatic privilege elevation.

Primary documentation consulted 2026-10-11:
- https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
- https://scikit-learn.org/stable/modules/cross_validation.html
- https://scikit-learn.org/stable/model_persistence.html
- https://pynput.readthedocs.io/en/latest/limitations.html
- https://doc.qt.io/qt-6/licensing.html
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
- https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html
- https://pyinstaller.org/en/stable/

Repository bootstrap evidence: first remote branch `dev`, initial SHA
1a3495b3308fbcedabb849b4fe69a3b29d1b58e6. The same minimal commit was then pushed
as `main`. GitHub rejected the first local bootstrap attempt for private email
protection; the unpublished commit was amended to the account's noreply email,
with no setting/visibility/permission changes. CLI GitHub API authentication was
unavailable, but git transport and the authorized GitHub connector worked.
