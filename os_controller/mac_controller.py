"""macOS controller: shared primitives, except where the Mac shortcut differs."""

import pyautogui
from pynput.keyboard import Key

from os_controller.base_controller import BaseOSController


class MacController(BaseOSController):
    # macOS switches windows/apps with Cmd+Tab, not Alt+Tab.
    _switch_modifier = Key.cmd

    def navigate_back(self):
        # macOS "Back" is Cmd+[ in browsers (Alt+Left does nothing here).
        pyautogui.hotkey("command", "[")
