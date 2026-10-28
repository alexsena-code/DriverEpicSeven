from copy import deepcopy

import pytest

from driver_epic_seven.config import load_config
from driver_epic_seven.windows import WindowProfileLease, verify_window


class FakeWindows:
    def __init__(self):
        self.window = {"hwnd": 100, "pid": 200, "process_name": "EpicSeven_Steam.exe",
                       "window_title": "Epic Seven", "window_class": "GLFW30",
                       "client_size": [1213, 682], "minimized": False, "foreground": False}
        self.current_style = 0x10CF0000
        self.resize_calls = []
        self.fail_once = False

    def inspect(self, hwnd):
        return deepcopy(self.window)

    def style(self, hwnd):
        return self.current_style

    def set_style(self, hwnd, style):
        self.current_style = style

    def resize_client(self, hwnd, size):
        self.resize_calls.append(list(size))
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("resize failed")
        self.window["client_size"] = list(size)


def test_connection_applies_profile_and_restores_resize_controls():
    windows = FakeWindows()
    original = windows.inspect(100)
    style = windows.current_style
    lease = WindowProfileLease(windows, original, load_config())
    assert windows.window["client_size"] == [1212, 682]
    assert not windows.current_style & WindowProfileLease.RESIZE_STYLE
    verify_window(windows.inspect(100), windows.inspect(100), load_config(), True)
    lease.close()
    assert windows.current_style == style
    assert windows.window["client_size"] == [1212, 682]
    count = len(windows.resize_calls)
    lease.close()
    assert len(windows.resize_calls) == count


def test_connection_failure_rolls_back_original_size_and_style():
    windows = FakeWindows()
    original, style = windows.inspect(100), windows.current_style
    windows.fail_once = True
    with pytest.raises(RuntimeError, match="resize failed"):
        WindowProfileLease(windows, original, load_config())
    assert windows.current_style == style
    assert windows.window["client_size"] == original["client_size"]


def test_disconnect_does_not_modify_reused_window_handle():
    windows = FakeWindows()
    lease = WindowProfileLease(windows, windows.inspect(100), load_config())
    windows.window["pid"] += 1
    calls = len(windows.resize_calls)
    lease.close()
    assert len(windows.resize_calls) == calls


def test_minimized_window_is_not_changed():
    windows = FakeWindows()
    windows.window["minimized"] = True
    style = windows.current_style
    with pytest.raises(RuntimeError, match="minimizada"):
        WindowProfileLease(windows, windows.inspect(100), load_config())
    assert windows.current_style == style
    assert not windows.resize_calls


def test_size_without_calibrated_profile_is_rejected(tmp_path):
    override = tmp_path / "unsupported.json"
    override.write_text('{"reference_size": [1280, 720]}', encoding="utf-8")
    with pytest.raises(ValueError, match="sem perfil calibrado"):
        load_config(str(override))


def test_external_size_change_still_blocks_input():
    windows = FakeWindows()
    lease = WindowProfileLease(windows, windows.inspect(100), load_config())
    original = windows.inspect(100)
    windows.window["client_size"] = [1200, 680]
    with pytest.raises(RuntimeError, match="Resolução"):
        verify_window(windows.inspect(100), original, load_config(), True)
    lease.close()
