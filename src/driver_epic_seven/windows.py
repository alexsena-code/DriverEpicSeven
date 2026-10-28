"""Consulta Win32 da janela; não lê memória nem injeta código no jogo."""

import ctypes as c
from ctypes import wintypes as w
from pathlib import PureWindowsPath
import sys


class Windows:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("O controle live requer Windows.")
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self._api(self.user, "IsWindow", w.BOOL, [w.HWND])
        self._api(self.user, "GetWindowTextW", c.c_int, [w.HWND, w.LPWSTR, c.c_int])
        self._api(self.user, "GetClassNameW", c.c_int, [w.HWND, w.LPWSTR, c.c_int])
        self._api(self.user, "GetWindowThreadProcessId", w.DWORD, [w.HWND, c.POINTER(w.DWORD)])
        self._api(self.user, "GetClientRect", w.BOOL, [w.HWND, c.POINTER(w.RECT)])
        self._api(self.user, "GetWindowRect", w.BOOL, [w.HWND, c.POINTER(w.RECT)])
        self._api(self.user, "GetWindowLongPtrW", c.c_ssize_t, [w.HWND, c.c_int])
        self._api(self.user, "SetWindowLongPtrW", c.c_ssize_t, [w.HWND, c.c_int, c.c_ssize_t])
        self._api(self.user, "SetWindowPos", w.BOOL, [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT])
        self._api(self.user, "IsIconic", w.BOOL, [w.HWND])
        self._api(self.user, "GetForegroundWindow", w.HWND, [])
        self._api(self.kernel, "OpenProcess", w.HANDLE, [w.DWORD, w.BOOL, w.DWORD])
        self._api(self.kernel, "CloseHandle", w.BOOL, [w.HANDLE])
        self._api(self.kernel, "QueryFullProcessImageNameW", w.BOOL,
                  [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)])
        try:
            self._api(self.user, "SetProcessDpiAwarenessContext", w.BOOL, [c.c_void_p])(c.c_void_p(-4))
        except AttributeError:
            self._api(self.user, "SetProcessDPIAware", w.BOOL, [])()

    @staticmethod
    def _api(lib, name, restype, args):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = restype, args
        return fn

    def inspect(self, hwnd: int) -> dict:
        if not self.user.IsWindow(hwnd):
            raise RuntimeError("A janela deixou de existir.")
        title, klass = c.create_unicode_buffer(512), c.create_unicode_buffer(256)
        self.user.GetWindowTextW(hwnd, title, len(title))
        self.user.GetClassNameW(hwnd, klass, len(klass))
        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not process:
            raise RuntimeError("Não foi possível identificar o processo da janela.")
        try:
            name = c.create_unicode_buffer(32768)
            size = w.DWORD(len(name))
            if not self.kernel.QueryFullProcessImageNameW(process, 0, name, c.byref(size)):
                raise c.WinError(c.get_last_error())
            executable = PureWindowsPath(name.value).name
        finally:
            self.kernel.CloseHandle(process)
        rect = w.RECT()
        if not self.user.GetClientRect(hwnd, c.byref(rect)):
            raise c.WinError(c.get_last_error())
        return {"hwnd": hwnd, "pid": pid.value, "process_name": executable,
                "window_title": title.value, "window_class": klass.value,
                "client_size": [rect.right-rect.left, rect.bottom-rect.top],
                "minimized": bool(self.user.IsIconic(hwnd)),
                "foreground": self.user.GetForegroundWindow() == hwnd}

    def discover(self, target: dict) -> dict:
        from maa.toolkit import Toolkit
        candidates = []
        names = {name.casefold() for name in target.get('process_names', [target.get('process_name', '')])}
        for window in Toolkit.find_desktop_windows():
            if window.window_name != target["window_title"] or window.class_name != target["window_class"]:
                continue
            hwnd = window.hwnd if isinstance(window.hwnd, int) else window.hwnd.value
            info = self.inspect(hwnd)
            if info["process_name"].casefold() in names:
                candidates.append(info)
        if len(candidates) != 1:
            raise RuntimeError(f"Esperada uma janela do jogo; encontradas {len(candidates)}.")
        return candidates[0]

    def style(self, hwnd):
        return self.user.GetWindowLongPtrW(hwnd, -16)

    def set_style(self, hwnd, style):
        c.set_last_error(0)
        old = self.user.SetWindowLongPtrW(hwnd, -16, style)
        if not old and c.get_last_error():
            raise c.WinError(c.get_last_error())
        if not self.user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x2|0x4|0x10|0x1|0x20):
            raise c.WinError(c.get_last_error())

    def resize_client(self, hwnd, size):
        current = self.inspect(hwnd)
        rect = w.RECT()
        if not self.user.GetWindowRect(hwnd, c.byref(rect)):
            raise c.WinError(c.get_last_error())
        width = rect.right-rect.left + size[0]-current["client_size"][0]
        height = rect.bottom-rect.top + size[1]-current["client_size"][1]
        if not self.user.SetWindowPos(hwnd, None, 0, 0, width, height, 0x2|0x4|0x10):
            raise c.WinError(c.get_last_error())
        if self.inspect(hwnd)["client_size"] != list(size):
            raise RuntimeError("O jogo não aceitou o tamanho calibrado da área cliente.")


class WindowProfileLease:
    """Apply the selected calibrated size; restore resize style on disconnect."""

    RESIZE_STYLE = 0x00040000 | 0x00010000  # WS_THICKFRAME | WS_MAXIMIZEBOX

    def __init__(self, windows, original, config):
        self.windows, self.original = windows, original
        self.hwnd = original["hwnd"]
        self.saved_style = windows.style(self.hwnd)
        self.target_size = list(config["reference_size"])
        self.active = False
        if original["minimized"]:
            raise RuntimeError("Janela minimizada; restaure antes de conectar.")
        policy = config.get("window_policy", {})
        self.active = True
        try:
            if policy.get("lock_resize_while_connected", False):
                windows.set_style(self.hwnd, self.saved_style & ~self.RESIZE_STYLE)
            if policy.get("resize_on_connect", False):
                windows.resize_client(self.hwnd, self.target_size)
            elif windows.inspect(self.hwnd)["client_size"] != self.target_size:
                raise RuntimeError("Resolução diferente da referência; calibração necessária.")
        except Exception:
            self.close(size=original["client_size"])
            raise

    def close(self, size=None):
        if not self.active:
            return
        self.active = False
        try:
            current = self.windows.inspect(self.hwnd)
        except (OSError, RuntimeError):
            return
        for key in ("pid", "process_name", "window_title", "window_class"):
            if current[key] != self.original[key]:
                return
        self.windows.set_style(self.hwnd, self.saved_style)
        self.windows.resize_client(self.hwnd, size or self.target_size)


def verify_window(current: dict, original: dict, config: dict, input_active=False):
    for key in ("hwnd", "pid", "process_name", "window_title", "window_class"):
        if current[key] != original[key]:
            raise RuntimeError("A identidade da janela mudou; execução interrompida.")
    if current["minimized"]:
        raise RuntimeError("Janela minimizada; este perfil não valida essa condição.")
    if current["client_size"] != config["reference_size"]:
        raise RuntimeError("Resolução diferente da referência; calibre o perfil antes de enviar entrada.")
    foreground_required = config["screencap_method"] == 32 or (
        input_active and (config["mouse_method"] == 1 or config["keyboard_method"] == 1)
    )
    if foreground_required and not current["foreground"]:
        raise RuntimeError("O método configurado requer o jogo em primeiro plano.")
