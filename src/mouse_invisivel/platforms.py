"""Replaceable native input adapters and diagnostics. No automatic elevation/consent."""
import os
import sys
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Monitor:
    name: str
    x: int
    y: int
    width: int
    height: int
    portal_stream: int | None = None

    def map(self, uv):
        xy = (round(self.x + float(uv[0]) * (self.width - 1)),
              round(self.y + float(uv[1]) * (self.height - 1)))
        return (*xy, self.portal_stream) if self.portal_stream is not None else xy

    def to_dict(self):
        return asdict(self)


def set_dpi_awareness():
    if sys.platform == "win32":
        import ctypes
        # Per-monitor v2, before creating any Qt/native window. May already be set by manifest.
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            ctypes.windll.shcore.SetProcessDpiAwareness(2)


def is_wayland():
    return sys.platform.startswith("linux") and (os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
                                                  or bool(os.environ.get("WAYLAND_DISPLAY")))


def input_allowed():
    if sys.platform.startswith("linux"):
        if is_wayland():
            return False, "Wayland requires explicit RemoteDesktop + GlobalShortcuts portal consent; use Autorizar portal. No XWayland fallback."
        if not os.environ.get("DISPLAY"):
            return False, "No X11 display. Preview/training need a desktop session."
    if sys.platform == "darwin":
        try:
            from HIServices import AXIsProcessTrusted
            if not AXIsProcessTrusted():
                return False, "Accessibility denied. Enable the running app in macOS Privacy & Security."
        except ImportError:
            return False, "HIServices accessibility diagnostics unavailable"
    return True, "Input permission preflight passed; physical operation still requires a manual test."


def monitors():
    if is_wayland():
        return []  # Only consented compositor-space portal coordinates are valid.
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        found = []
        class Info(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("rect", wintypes.RECT),
                        ("work", wintypes.RECT), ("flags", wintypes.DWORD), ("device", wintypes.WCHAR * 32)]
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                           ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        def collect(handle, _dc, _rect, _data):
            info = Info()
            info.size = ctypes.sizeof(Info)
            if ctypes.windll.user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                r = info.rect
                found.append(Monitor(info.device, r.left, r.top, r.right-r.left, r.bottom-r.top))
            return True
        ctypes.windll.user32.GetMonitorInfoW.argtypes = (wintypes.HMONITOR, ctypes.POINTER(Info))
        ctypes.windll.user32.GetMonitorInfoW.restype = wintypes.BOOL
        ctypes.windll.user32.EnumDisplayMonitors.argtypes = (wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                                            callback_type, wintypes.LPARAM)
        callback = callback_type(collect)
        ctypes.windll.user32.EnumDisplayMonitors(None, None, callback, 0)
        return found
    if sys.platform == "darwin":
        import Quartz
        err, ids, _ = Quartz.CGGetActiveDisplayList(32, None, None)
        if err:
            raise RuntimeError(f"CGGetActiveDisplayList failed: {err}")
        result = []
        for display_id in ids:
            r = Quartz.CGDisplayBounds(display_id)
            result.append(Monitor(str(display_id), int(r.origin.x), int(r.origin.y),
                                  int(r.size.width), int(r.size.height)))
        # Quartz cursor coordinates use display points, including Retina, not backing pixels.
        return result
    if sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
        from Xlib import display
        from Xlib.ext import randr
        d = display.Display()
        try:
            if d.has_extension("RANDR"):
                try:
                    reply = randr.get_monitors(d.screen().root, True)
                    result = [Monitor(str(d.get_atom_name(m.name)), m.x, m.y, m.width, m.height)
                              for m in reply.monitors]
                    if result:
                        return result
                except Exception:
                    pass  # Older XRandR servers: safe full-root virtual-screen fallback.
            root = d.screen()
            return [Monitor("X11 virtual desktop", 0, 0, root.width_in_pixels, root.height_in_pixels)]
        finally:
            d.close()
    return []


class RecordingAdapter:
    """Test/preview adapter. Never imported as a fallback for live input."""
    def __init__(self):
        self.events = []
        self.held = set()

    def move(self, xy):
        self.events.append(("move", tuple(xy)))

    def press(self, button):
        self.held.add(button)
        self.events.append(("press", button))

    def release(self, button):
        if button in self.held:
            self.held.remove(button)
            self.events.append(("release", button))

    def scroll(self, amount):
        self.events.append(("scroll", amount))

    def check(self):
        pass


class PynputAdapter:
    """macOS Quartz / Linux XTest backend, with platform-specific permission preflight."""
    def __init__(self):
        self.check()
        if sys.platform.startswith("linux"):
            from Xlib import display
            d = display.Display()
            try:
                if not d.has_extension("XTEST"):
                    raise RuntimeError("XTest extension unavailable; input disabled")
            finally:
                d.close()
        from pynput.mouse import Controller, Button
        self.controller = Controller()
        self.buttons = {"left": Button.left, "right": Button.right}
        self.held = set()

    def check(self):
        allowed, reason = input_allowed()
        if not allowed:
            raise RuntimeError(reason)

    def move(self, xy):
        self.check()
        self.controller.position = xy

    def press(self, button):
        self.check()
        self.held.add(button)  # Keep ownership even if the native call partially fails.
        self.controller.press(self.buttons[button])

    def release(self, button):
        # Release still attempts cleanup after permission revocation.
        if button in self.held:
            self.controller.release(self.buttons[button])
            self.held.remove(button)

    def scroll(self, amount):
        self.check()
        self.controller.scroll(0, amount)


class WindowsAdapter:
    """Checked SendInput; no elevation and no injection into a higher-integrity target."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        set_dpi_awareness()
        self.ctypes = ctypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.restype = wintypes.UINT
        class MouseInput(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("data", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("extra", ctypes.c_size_t)]
        class KeyboardInput(ctypes.Structure):
            _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD), ("flags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]
        class HardwareInput(ctypes.Structure):
            _fields_ = [("message", wintypes.DWORD), ("low", wintypes.WORD), ("high", wintypes.WORD)]
        class Payload(ctypes.Union):
            # Include keyboard/hardware so INPUT has the correct size on x86 and x64.
            _fields_ = [("mouse", MouseInput), ("keyboard", KeyboardInput), ("hardware", HardwareInput)]
        class Input(ctypes.Structure):
            _fields_ = [("kind", wintypes.DWORD), ("payload", Payload)]
        self.MouseInput, self.Payload, self.Input = MouseInput, Payload, Input
        self.user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int)
        self.held = set()

    def check(self):
        pass  # SendInput's return value is the authoritative operation result.

    def send(self, flags, dx=0, dy=0, data=0):
        c = self.ctypes
        event = self.Input(0, self.Payload(mouse=self.MouseInput(dx, dy, data & 0xffffffff, flags, 0, 0)))
        if self.user32.SendInput(1, c.byref(event), c.sizeof(event)) != 1:
            raise RuntimeError(f"SendInput rejected (error {c.get_last_error()}); check integrity/desktop restrictions")

    def move(self, xy):
        # Normalize against the physical virtual desktop, including negative monitor origins.
        x, y = self.user32.GetSystemMetrics(76), self.user32.GetSystemMetrics(77)
        w, h = self.user32.GetSystemMetrics(78), self.user32.GetSystemMetrics(79)
        if w <= 1 or h <= 1:
            raise RuntimeError("Invalid Windows virtual desktop")
        dx = round((xy[0]-x) * 65535 / (w-1))
        dy = round((xy[1]-y) * 65535 / (h-1))
        self.send(0x0001 | 0x8000 | 0x4000, min(65535, max(0, dx)), min(65535, max(0, dy)))

    def press(self, button):
        self.held.add(button)
        self.send(0x0002 if button == "left" else 0x0008)

    def release(self, button):
        if button in self.held:
            self.send(0x0004 if button == "left" else 0x0010)
            self.held.remove(button)

    def scroll(self, amount):
        self.send(0x0800, data=amount * 120)


def make_adapter():
    allowed, reason = input_allowed()
    if not allowed:
        raise RuntimeError(reason)
    return WindowsAdapter() if sys.platform == "win32" else PynputAdapter()


def diagnostics():
    allowed, reason = input_allowed()
    try:
        screens = [m.to_dict() for m in monitors()]
        screen_error = None
    except Exception as e:
        screens, screen_error = [], str(e)
    portal = None
    if is_wayland():
        from .wayland import probe_sync
        portal = probe_sync()
    return {"platform": sys.platform, "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "input_preflight": allowed, "input_detail": reason, "monitors": screens,
            "monitor_error": screen_error, "camera": "Not opened; explicit preview required",
            "camera_privacy": "No raw recording/upload. Denial/revocation/unplug cause pause.",
            "wayland_portal": portal, "manual_validation": "Not established by this diagnostic"}
