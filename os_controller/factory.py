"""Pick the right OS controller for the current platform."""

import platform

from os_controller.base_controller import BaseOSController
from os_controller.linux_controller import LinuxController
from os_controller.mac_controller import MacController
from os_controller.windows_controller import WindowsController


def create_os_controller() -> BaseOSController:
    system = platform.system()
    if system == "Windows":
        return WindowsController()
    if system == "Darwin":
        return MacController()
    return LinuxController()
