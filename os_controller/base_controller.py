"""
BaseOSController: the OS-facing primitives, implemented with pyautogui + pynput.

Both libraries are cross-platform, so the shared implementation lives here and the
per-OS subclasses only override what actually differs (e.g. how to read the screen
size). Adding a new platform later means one small subclass, not scattered
`if windows:` checks throughout the codebase.
"""

import pyautogui
from pynput.keyboard import Controller as KeyboardInput
from pynput.keyboard import Key
from pynput.mouse import Button
from pynput.mouse import Controller as MouseInput

# Moving into a screen corner would trip pyautogui's fail-safe and crash; we clamp
# coordinates ourselves in the mapper, so disable it.
pyautogui.FAILSAFE = False
# pyautogui sleeps 0.1s after every call by default, which throttles the whole loop
# (laggy cursor, scroll barely registers). We drive it every frame, so remove it.
pyautogui.PAUSE = 0


class BaseOSController:
    # Modifier the window switcher holds down. Alt on Windows/Linux; MacController
    # overrides it with Cmd (macOS uses Cmd+Tab).
    _switch_modifier = Key.alt

    def __init__(self):
        self._mouse = MouseInput()  # pynput handle for reliable press/release (drag)
        self._kb = KeyboardInput()  # pynput handle for holding the switcher modifier
        self._switch_open = False   # is the switcher modifier currently held down?

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

    # -- Alt+Tab window switcher (modifier held down across frames) --------
    def _tap_tab(self):
        self._kb.press(Key.tab)
        self._kb.release(Key.tab)

    def alt_tab_open(self):
        # Press the modifier and KEEP it down so the switcher stays open, then Tab
        # once to move onto the next window (the usual first step of Alt+Tab).
        if not self._switch_open:
            self._kb.press(self._switch_modifier)
            self._switch_open = True
        self._tap_tab()

    def alt_tab_next(self):
        self._tap_tab()  # modifier still held -> highlight the next window

    def alt_tab_prev(self):
        # Shift+Tab walks the switcher backwards, modifier still held.
        self._kb.press(Key.shift)
        self._tap_tab()
        self._kb.release(Key.shift)

    def alt_tab_commit(self):
        # Release the modifier -> the highlighted window is selected. Guarded so it's
        # a harmless no-op when the switcher isn't open (used by the exit safety net).
        if self._switch_open:
            self._kb.release(self._switch_modifier)
            self._switch_open = False
