"""macOS controller: shared primitives, except where the Mac shortcut differs."""

import pyautogui

from os_controller.base_controller import BaseOSController


class MacController(BaseOSController):
    def navigate_back(self):
        # macOS "Back" is Cmd+[ in browsers (Alt+Left does nothing here).
        pyautogui.hotkey("command", "[")
