"""
CoordinateMapper: camera-frame point -> screen pixel.

Maps the inset "active region" of the camera frame onto the full screen so you
don't have to reach the physical edges of the camera's field of view. Pure math,
OS-independent - the MouseController owns smoothing and the actual cursor move.
"""

import numpy as np

import config
from utils.math_utils import clamp

Point = tuple


class CoordinateMapper:
    def __init__(self, cam_w: int, cam_h: int, screen_w: int, screen_h: int):
        self.cam_w = cam_w
        self.cam_h = cam_h
        self.screen_w = screen_w
        self.screen_h = screen_h

    def to_screen(self, point):
        x, y = point
        left, right = config.FRAME_MARGIN_LEFT, config.FRAME_MARGIN_RIGHT
        top, bottom = config.FRAME_MARGIN_TOP, config.FRAME_MARGIN_BOTTOM

        # Where the point sits inside the box, 0..1 on each axis.
        nx = np.interp(x, (left, self.cam_w - right), (0.0, 1.0))
        ny = np.interp(y, (top, self.cam_h - bottom), (0.0, 1.0))

        # Amplify around the centre (0.5) so a comfortable inner range of hand
        # movement reaches the screen edges - you don't have to stretch your
        # fingertip all the way to the box corner to hit a screen corner. Clamped
        # below, so overshooting past an edge just pins the cursor there.
        g = config.CURSOR_SENSITIVITY
        nx = 0.5 + (nx - 0.5) * g
        ny = 0.5 + (ny - 0.5) * g

        sx = nx * self.screen_w
        sy = ny * self.screen_h
        return clamp(sx, 0, self.screen_w - 1), clamp(sy, 0, self.screen_h - 1)
