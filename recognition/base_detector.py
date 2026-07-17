"""
Detector interface + the context passed to every detector.

Each gesture (move, click/pinch, right-click, two-finger scroll, hold)
is its own small detector implementing `detect()`. This keeps every gesture's
rules isolated and testable instead of piling them into one giant if/elif method.
A detector returns a `GestureEvent` when its gesture is active, else `None`.
"""

from dataclasses import dataclass
from typing import List, Optional

from config import Thresholds
from core.gestures import GestureEvent
from core.landmark import HandLandmarks


@dataclass
class DetectContext:
    """Everything a detector needs beyond the hands themselves."""

    thresholds: Thresholds
    now: float  # current timestamp (seconds); passed in so timing is testable


class BaseDetector:
    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        raise NotImplementedError

    def reset(self):
        """Clear any per-gesture state (called on pause/stop)."""
