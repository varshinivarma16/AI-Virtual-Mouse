"""Windows controller: screen size via screeninfo, and a robust wheel scroll.

Scrolling here goes through SendInput rather than pyautogui or PostMessage.

`pyautogui.scroll()` was the first attempt: it injects a wheel event that Windows
routes to the *focused* window - usually the preview window or the terminal, not
the page you're pointing at.

PostMessageW(WM_MOUSEWHEEL) was the second: it targets the window under the cursor
directly, but Chrome, Electron apps and anything else with a separate compositor
thread ignore *posted* wheel messages - they only consume input that arrives via
the real input queue. The call succeeds and nothing scrolls.

SendInput injects at the driver level, so the event enters the input queue like a
physical wheel and Windows delivers it to the window under the cursor (the
"scroll inactive windows when I hover over them" setting, on by default since
Win10). This is what actually scrolls a browser.
"""

import ctypes
from ctypes import wintypes

from os_controller.base_controller import BaseOSController

_INPUT_MOUSE = 0
_MOUSEEVENTF_WHEEL = 0x0800
_WHEEL_DELTA = 120  # one notch of the wheel

# A PRIVATE user32 handle. `ctypes.windll.user32` is a process-wide singleton whose
# function objects are shared, so setting .argtypes on its SendInput would rebind the
# very same object pynput calls - and pynput's INPUT struct would then be rejected
# against our _INPUT, breaking every click in the app. WinDLL() builds a separate
# instance with its own function cache, so our argtypes stay ours.
_user32 = ctypes.WinDLL("user32")

# ULONG_PTR isn't in wintypes; it's pointer-sized (8 bytes on x64, 4 on x86).
_ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(_ULONG_PTR)),
    ]


class _INPUT(ctypes.Structure):
    class _UNION(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _UNION)]


_user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
_user32.SendInput.restype = wintypes.UINT


class WindowsController(BaseOSController):
    def screen_size(self):
        try:
            from screeninfo import get_monitors

            monitor = get_monitors()[0]
            return (monitor.width, monitor.height)
        except Exception:
            # Fall back to pyautogui if screeninfo can't read the monitor list.
            return super().screen_size()

    def scroll(self, amount, pos=None):
        notches = int(round(amount))
        if notches == 0:
            return
        # mouseData is a signed wheel delta, but the field is a DWORD - mask it to
        # 32 bits so negative (scroll-down) values survive the conversion.
        delta = notches * _WHEEL_DELTA  # >0 = scroll up
        event = _INPUT(
            type=_INPUT_MOUSE,
            mi=_MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=delta & 0xFFFFFFFF,
                dwFlags=_MOUSEEVENTF_WHEEL,
                time=0,
                dwExtraInfo=None,
            ),
        )
        _user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(_INPUT))
