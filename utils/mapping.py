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
        mx, my = config.FRAME_MARGIN_X, config.FRAME_MARGIN_Y
        sx = np.interp(x, (mx, self.cam_w - mx), (0, self.screen_w))
        sy = np.interp(y, (my, self.cam_h - my), (0, self.screen_h))
        return clamp(sx, 0, self.screen_w - 1), clamp(sy, 0, self.screen_h - 1)
