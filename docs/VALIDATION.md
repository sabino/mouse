# Verification evidence

Snapshot 2026-10-11. This environment has no physical camera or interactive OS-input
validation. A working headless build is not proof of real hardware usability.

| State | Evidence | Limit |
|---|---|---|
| Built core | `dev` ee11dba3facb3ca86200ac58fa88529f7d62899d, draft PR #5 | Desktop is stacked on feat/desktop |
| Unit/synthetic replay | 15 local tests passing, classifier numeric round-trip checked against sklearn | Mathematical fixtures, not recorded physical hand data |
| Mocked input | Ownership, partial native failure, stale timestamps, watchdog, neutral/rejection, Wayland refusal | No physical input/camera |
| Headless desktop | Qt offscreen capture/label/train/reload/preview test + GUI smoke | Synthetic packet; no real camera/model detection |
| Core CI | https://github.com/sabino/mouse/actions/runs/38168215710 successful | Three OS test jobs, 11 core tests; not physical input |
| Linux native package | PyInstaller directory built and diagnostics/GUI smoke passed locally | Cloud Linux, headless; final revised build pending |
| Full desktop/native CI | Pending stacked draft PR workflow | Three OS packaging + smoke, not physical hardware |
| Physical camera/input | NOT TESTED on macOS/Windows/Linux | Requires user's hardware + real personally recorded sessions |
| Native Wayland input | Explicitly unavailable | Preview/label/train only |
| Reference analysis | Transcript inaccessible | No timestamps/algorithm details inferred |
| Hand Landmarker weights | Versioned official URL returned HTTP 403 in Cloud | No bypass; user selects licensed local .task, not redistributed |
| Distribution license/signing | Inventory generated; final embedded native/Qt notices review and signing pending | No release/public distribution |

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
states to #3/#4. Capture sensor-buffer freshness and whole-system latency cannot be proven
in this Cloud. Emergency stop must be physically verified before each new input worker.
