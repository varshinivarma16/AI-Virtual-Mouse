"""
Small geometry helpers.

Named `math_utils` rather than `math` on purpose: a module called `math.py` on the
import path can shadow Python's standard-library `math`, which is a classic and
hard-to-debug footgun. Same helpers you asked for, just a safe name.
"""

import math
from typing import Tuple

Point = Tuple[float, float]


def distance(p1: Point, p2: Point) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation: t=0 -> a, t=1 -> b."""
    return a + (b - a) * t
