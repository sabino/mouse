# Verification evidence

Snapshot 2026-10-12. This environment has no physical camera or interactive OS-input
validation. A working headless build is not proof of real hardware usability.

| State | Evidence | Limit |
|---|---|---|
| Built core | `dev` 3af89a2abb069c36fc9aaef5bd7b487cf6abd8bf, PR #5 | Main integration and desktop PR #6 state are recorded in PR comments |
| Unit/synthetic replay | 43 local tests passing + 2 native bridge/ABI tests skipped on Linux, classifier numeric round-trip checked against sklearn | Mathematical fixtures, not recorded physical hand data |
| Mocked input | Ownership, partial native failure, stale timestamps, watchdog, neutral/rejection, degenerate-feature/hand-switch drag release, delayed production-worker shutdown, Wayland refusal | No physical input/camera |
| Headless desktop | Qt offscreen capture/label/train/reload/preview test + GUI smoke | Synthetic packet; no real camera/model detection |
| Core CI | https://github.com/sabino/mouse/actions/runs/38198463681 successful at 3af89a2 | Three OS core/safety/schema jobs; not physical input |
| Linux native package | PyInstaller directory built and diagnostics/GUI smoke passed locally | Cloud Linux, headless; frozen worker probe and synthetic train/reload/replay also passed |
| Desktop/native CI before portals | https://github.com/sabino/mouse/actions/runs/38170728954 at 96c38ef: all three source/native/frozen checks passed; Linux 19 pass/2 skip, macOS/Windows 20 pass/1 skip | Workflow red solely on upload quota; latest PR check/comments report subsequent portal head |
| Physical camera/input | NOT TESTED on macOS/Windows/Linux | Requires user's hardware + real personally recorded sessions |
| Native Wayland protocol | 11 private D-Bus cases: fake portal, actual dbus-daemon/service activation and production spawned worker; no OS consent/input | Physical compositor not tested; Sway/wlr lacks RemoteDesktop/GlobalShortcuts (issue #8) |
| Reference analysis | Transcript inaccessible | No timestamps/algorithm details inferred |
| Hand Landmarker weights | Follow-up request failed at proxy CONNECT: Tunnel connection failed: 403 Forbidden | No model-server response/bytes; no bypass; license still unverified |
| GitHub artifact delivery | Historical private-repository uploads hit storage quota; the owner made the repo public | New archives preserve Unix executable bits/symlinks and include provenance/hash. Actual download evidence is attached to #6/#7; do not infer delivery from source checks |
| Private Library delivery | Supported helper retry failed on hosted apps tools/list network | No saved Library file/link returned; preserved 96c38ef archive checksum in #7 |
| Distribution license/signing | Inventory generated; final embedded native/Qt notices review and signing pending | Draft Actions/local artifacts only; no release published |

Actual-hand replay can run with no OS input:

```sh
mouse-invisivel --replay session.json --model gesture-model.json --profile profile.json
```

CLI training uses the same pipeline as the desktop and also injects no input:

```sh
mouse-invisivel --train session1.json session2.json --holdout SESSION2_ID --output gesture-model.json
```

Tests synthesize mathematical fixtures explicitly marked `synthetic-test`; they never
become product example data. Real event/idle metrics exist only after recording actual
sessions. Before calling any platform usable, complete [manual checks](PLATFORMS.md)
and attach observations/diagnostics, camera model, display layout, OS version and permission
states to #1/#4/#7. Capture sensor-buffer freshness and whole-system latency cannot be proven
in this Cloud. Emergency stop must be physically verified before each new input worker.

Review regressions cover oversized UTF-8 JSON preserving the prior file, exact byte
boundaries, 32/33 model classes and mappings, 1000/1001 session clips, constant-feature
Gaussian numeric persistence, replay drag release on gaps/out-of-order frames and GUI
capture budgets with a reloadable saved session. Saves use the same schemas as loaders;
the data schema/byte limits are enforced before atomic replacement.

Native packages use a tar archive on Linux/macOS (preserves launcher permissions and
framework symlinks) and ZIP on Windows. Build/package guards require a clean, unchanged
commit. Each archive includes BUILD-INFO.json and dependency licenses; artifact-index.json
and SHA256SUMS.txt describe the exact native archive bytes. CI verifies archives before
upload; maintainer review must also download them and confirm delivery independently.
