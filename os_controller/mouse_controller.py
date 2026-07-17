"""
MouseController: executes ActionCommands on the real machine.

It sits above the per-OS controller and adds the two things that need screen and
camera context: mapping a camera point to a screen pixel, and smoothing the cursor
so it doesn't jitter. Everything OS-specific is delegated to the platform
controller chosen by the factory.
"""

import config
from core.gestures import Action, ActionCommand
from os_controller.factory import create_os_controller
from utils.logging_setup import get_logger
from utils.mapping import CoordinateMapper
from utils.math_utils import clamp, distance, lerp


class MouseController:
    def __init__(self, cam_w: int, cam_h: int):
        self.os = create_os_controller()
        screen_w, screen_h = self.os.screen_size()
        self.mapper = CoordinateMapper(cam_w, cam_h, screen_w, screen_h)
        self._prev = (screen_w / 2, screen_h / 2)  # smoothed cursor position
        self._scroll_residual = 0.0  # sub-notch scroll carried to the next frame
        self._log = get_logger()
        self._log.info(
            "MouseController ready (%s, screen %dx%d)",
            type(self.os).__name__,
            screen_w,
            screen_h,
        )

    def _place(self, point):
        """Map a camera point to screen, then smooth and stabilize the cursor.

        Adaptive exponential smoothing: slow/fine hand moves are smoothed hard so
        the cursor is steady enough to click a small target, while fast moves pass
        through with little lag. A dead-zone holds the cursor still against hand
        tremor so it doesn't drift off a button while you go to pinch-click.
        """
        sx, sy = self.mapper.to_screen(point)
        px, py = self._prev

        moved = distance((sx, sy), (px, py))
        if moved < config.CURSOR_DEADZONE:
            return px, py  # hand basically still -> hold, so aiming stays put

        # Blend smoothing by speed: slow -> MIN_ALPHA (smooth), fast -> MAX_ALPHA.
        t = clamp(moved / config.SMOOTHING_SPEED_SCALE, 0.0, 1.0)
        alpha = lerp(config.SMOOTHING_MIN_ALPHA, config.SMOOTHING_MAX_ALPHA, t)
        cx = px + (sx - px) * alpha
        cy = py + (sy - py) * alpha
        self._prev = (cx, cy)
        return cx, cy

    def _scroll(self, amount: float):
        """Scroll by whole wheel notches, banking the fraction for the next frame.

        The wheel only moves in whole notches, so rounding each frame in isolation
        would throw away every swipe under half a notch - a slow, deliberate swipe
        would emit SCROLL and move nothing. Carrying the remainder means the page
        travels the distance the hand actually swept, however slowly it's swept.
        """
        self._scroll_residual += amount
        notches = int(self._scroll_residual)  # truncates toward zero, so sign is kept
        if notches:
            self._scroll_residual -= notches
            self.os.scroll(notches, self._prev)

    def execute(self, cmd: ActionCommand):
        a = cmd.action

        if a == Action.MOVE:
            self.os.move_to(*self._place(cmd.point))
        elif a == Action.LEFT_CLICK:
            self.os.left_click()
        elif a == Action.RIGHT_CLICK:
            self.os.right_click()
        elif a == Action.DOUBLE_CLICK:
            self.os.double_click()
        elif a == Action.SCROLL:
            self._scroll(cmd.amount * config.SCROLL_MULTIPLIER)
        elif a == Action.MEDIA_PLAY_PAUSE:
            self.os.media_play_pause()
        elif a == Action.NAVIGATE_BACK:
            self.os.navigate_back()
        elif a == Action.ALT_TAB_OPEN:
            self.os.alt_tab_open()
        elif a == Action.ALT_TAB_NEXT:
            self.os.alt_tab_next()
        elif a == Action.ALT_TAB_PREV:
            self.os.alt_tab_prev()
        elif a == Action.ALT_TAB_COMMIT:
            self.os.alt_tab_commit()
        elif a == Action.DRAG_START:
            self.os.move_to(*self._place(cmd.point))
            self.os.mouse_down()
        elif a == Action.DRAG_MOVE:
            self.os.move_to(*self._place(cmd.point))
        elif a == Action.DRAG_END:
            self.os.mouse_up()

        self._log.debug("executed %s", a.name)

    def release_all(self):
        """Safety: make sure nothing is left held down on pause/exit.

        A stuck Alt key from an interrupted switch would wreck every keystroke after
        it, so releasing the switcher modifier here is as important as the mouse.
        """
        self.os.mouse_up()
        self.os.alt_tab_commit()
