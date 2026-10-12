"""Native read-only bridge checks. No camera, permission requests or input injection."""
import ctypes
import sys
import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="Requires macOS bridge")
def test_macos_accessibility_bridge_exists_and_does_not_prompt():
    from HIServices import AXIsProcessTrusted
    from mouse_invisivel.platforms import input_allowed
    assert isinstance(AXIsProcessTrusted(), (bool, int))
    _, detail = input_allowed()
    assert "unavailable" not in detail


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows ABI")
def test_windows_input_abi_and_virtual_monitor_math_without_injection(monkeypatch):
    from mouse_invisivel.platforms import WindowsAdapter
    adapter = WindowsAdapter()
    assert ctypes.sizeof(adapter.Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    captured = []
    monkeypatch.setattr(adapter, "send", lambda *args, **kwargs: captured.append((args, kwargs)))
    x, y = adapter.user32.GetSystemMetrics(76), adapter.user32.GetSystemMetrics(77)
    w, h = adapter.user32.GetSystemMetrics(78), adapter.user32.GetSystemMetrics(79)
    adapter.move((x+w//2, y+h//2))
    args, _ = captured[-1]
    assert 0 <= args[1] <= 65535 and 0 <= args[2] <= 65535
    assert args[0] & 0x4000  # Physical virtual-desktop flag, including negative origins.
    assert not adapter.held
