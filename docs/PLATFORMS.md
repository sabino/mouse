# Platform behavior and physical acceptance

Windows calls SetProcessDpiAwarenessContext (per-monitor v2) before Qt/monitor queries.
EnumDisplayMonitors gives physical rectangles, including negative coordinates. SendInput
absolute motion uses the entire physical virtual desktop. Its return count is checked;
UIPI/high-integrity applications, locked screens and secure desktops are not bypassed.
No automatic administrator elevation. Windows artifacts are unsigned directory builds.

macOS uses native Quartz global display bounds/cursor points (Retina backing pixels are
not multiplied into pointer coordinates). AXIsProcessTrusted is checked without prompting
or granting permission. Camera errors become visible and pause control; enable Camera in
Privacy & Security manually. The global Esc listener may require Input Monitoring as well
as Accessibility. Verify Esc physically before activation. Camera permission applies to the
running binary/interpreter; moving/rebuilding an app can require renewed permission. Native
app bundles carry NSCameraUsageDescription and are locally ad-hoc signed; not notarized.

Linux requires an X11 display and XTest for input. XRandR monitor rectangles are physical
server coordinates; old servers fall back to one full-root virtual desktop. `pynput` is
not presented as a native Wayland adapter: WAYLAND_DISPLAY or XDG_SESSION_TYPE=wayland
explicitly blocks input even if an XWayland DISPLAY exists. Preview, labeling and training
can still run. A future consent-based RemoteDesktop portal/libei adapter is tracked, not
implemented. No uinput permissions/groups are granted and no root access is required.

Camera index changes, handedness/profile/model changes, capture/training/calibration,
explicit pause and shutdown all pause input. Missing/wrong/ambiguous hand, tracking gaps,
old or out-of-order frames and inference errors stop actions. Stale capture timestamps
include capture+inference latency; OpenCV buffer size is best-effort, not proof that a
particular camera driver delivered a fresh sensor image. Confirm latency physically.

Invalid/degenerate feature windows and hand switches now emit release, disarm and clear
feature history; only initial incomplete windows use warm-up. A reduced feature window
while dragging also fails closed.

The input worker runs separately from capture/inference/UI, rejects stale queued commands,
and releases only buttons it owns after >350 ms without fresh command timestamps. Pause
increments a shared generation so queued earlier actions cannot reactivate. The worker
checks listener health, permission preflight and native monitor topology. Display changes
pause and require refreshed diagnostics. Invalid/uncertain gesture predictions produce no
new actions and safely release an app-held drag. Stable neutral re-arms episodes. A global
Esc reception test is required before activation. App-window Esc and the stop button always
pause. The worker can release on a hung/crashed parent while alive; forced killing of the
worker, OS failures or permission revocation that also prevents release are unavoidable
limitations. The worker is non-daemon and acknowledges completed release. Closing remains pending
with controls disabled if cleanup exceeds its wait; the GUI closes only after acknowledgement
and worker completion. Failed releases remain owned and are retried; no timeout forcibly
terminates cleanup. OS/app quit requests stop fresh input, and Python waits for the
non-daemon worker. Forced OS termination still cannot be made safe by a finally block.
Release failures are surfaced; restore permission/focus if native release is rejected.

Manual acceptance, on EACH real target platform:
1. Install/build, obtain licensed landmarks, open preview. Check mirrored handedness and
   no input until explicit activation. Verify no network traffic/raw file recording.
2. Capture real positives/neutral/confusing movements over separate days. Train, inspect
   holdout event/idle diagnostics, save/reload profile/model and run preview trials.
3. Calibrate five comfortable-range targets. Test chosen monitor, negative origins,
   100/150/200% scaling, Retina/mixed DPI and sensitivity/smoothing. Change monitor layout
   while dragging: expect pause/release and explicit restart.
4. Verify Esc globally while another application is focused. Then test pointer, primary,
   secondary, drag/release, scroll and custom mappings in a disposable drawing app.
5. Cover one/multiple hands, wrong handedness, partial/confusing poses, low confidence,
   repeated gesture without neutral, camera cover/unplug/reconnect, access denial/revocation,
   sleep/resume, CPU stall and deliberate inference/UI hang. Check app-held release.
6. Check lower/higher-integrity Windows targets, macOS permission changes, X11 permission/
   display loss, native Wayland refusal. Record latency, idle false activations and user
   observations; do not infer success from CI or the mock adapter.
