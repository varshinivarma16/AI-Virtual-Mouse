"""
PinchDetector: the thumb+index pinch lifecycle.

It only reports the raw lifecycle - START (just met), HOLD (still pinched, with
seconds-held), END (just released, with seconds-held). It deliberately does NOT
decide "click vs drag"; that policy lives in the ActionEngine, so the same pinch
could later be remapped to something else entirely.

The pinch is measured RELATIVE TO THE PALM, not in raw camera pixels. Pixel
distances shrink as the hand moves away from the camera, so a fixed pixel
threshold that feels right up close turns into a hair-trigger further back -
fingers that are merely near each other read as touching, and the app clicks on
its own. Dividing by the palm span makes the threshold mean the same thing at any
distance.
"""

from typing import List, Optional

from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext
from utils.math_utils import distance


class PinchDetector(BaseDetector):
    def __init__(self):
        self._start = None  # timestamp the current pinch began, or None

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self._start = None
            return None

        hand = hands[0]
        point = hand.tip(1).xy
        # Thumb-index gap as a fraction of the palm: ~0.1 touching, ~1.0 spread.
        gap = distance(hand.tip(0).xy, hand.tip(1).xy) / hand.palm_size()

        # Hysteresis: it takes a real touch to start a pinch, but a clearly wider
        # gap to end one. With a single threshold, a hand resting near the boundary
        # jitters across it and machine-guns clicks.
        if self._start is None:
            pinching = gap < ctx.thresholds.pinch_ratio
        else:
            pinching = gap < ctx.thresholds.pinch_ratio * ctx.thresholds.pinch_release

        if pinching:
            if self._start is None:
                self._start = ctx.now
                return GestureEvent(Gesture.PINCH_START, point=point, hand_label=hand.label)
            held = ctx.now - self._start
            return GestureEvent(Gesture.PINCH_HOLD, point=point, value=held, hand_label=hand.label)

        # not pinching
        if self._start is not None:
            held = ctx.now - self._start
            self._start = None
            return GestureEvent(Gesture.PINCH_END, point=point, value=held, hand_label=hand.label)
        return None

    def reset(self):
        self._start = None
