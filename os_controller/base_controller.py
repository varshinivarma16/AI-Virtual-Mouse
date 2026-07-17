"""
BaseOSController: the OS-facing primitives, implemented with pyautogui + pynput.

Both libraries are cross-platform, so the shared implementation lives here and the
per-OS subclasses only override what actually differs (e.g. how to read the screen
size). Adding a new platform later means one small subclass, not scattered
`if windows:` checks throughout the codebase.
"""

import pyautogui
from pynput.mouse import Button
from pynput.mouse import Controller as MouseInput

# Moving into a screen corner would trip pyautogui's fail-safe and crash; we clamp
# coordinates ourselves in the mapper, so disable it.
pyautogui.FAILSAFE = False
# pyautogui sleeps 0.1s after every call by default, which throttles the whole loop
# (laggy cursor, scroll barely registers). We drive it every frame, so remove it.
pyautogui.PAUSE = 0


class BaseOSController:
    def __init__(self):
        self._mouse = MouseInput()  # pynput handle for reliable press/release (drag)

    # -- screen ------------------------------------------------------------
    def screen_size(self):
        return pyautogui.size()

    # -- pointer -----------------------------------------------------------
    def move_to(self, x, y):
        pyautogui.moveTo(x, y)

    def left_click(self):
        pyautogui.click()

    def right_click(self):
        pyautogui.click(button="right")

    def double_click(self):
        pyautogui.doubleClick()

    def scroll(self, amount, pos=None):
        # Scroll AT a screen position when given one: the OS sends the wheel event
        # to whatever window is under that point, so the page you're pointing at
        # scrolls even if it isn't the focused window.
        if pos is not None:
            pyautogui.scroll(int(amount), x=int(pos[0]), y=int(pos[1]))
        else:
            pyautogui.scroll(int(amount))

    # -- media -------------------------------------------------------------
    def media_play_pause(self):
        pyautogui.press("playpause")  # global media key: pauses/plays videos

    # -- navigation --------------------------------------------------------
    def navigate_back(self):
        # Alt+Left is "Back" in browsers and file explorers on Windows and Linux.
        # macOS uses a different shortcut - see MacController.
        pyautogui.hotkey("alt", "left")

    # -- drag (button held down across moves) ------------------------------
    def mouse_down(self):
        self._mouse.press(Button.left)

    def mouse_up(self):
        self._mouse.release(Button.left)
