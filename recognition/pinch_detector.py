"""
PinchDetector: the thumb+index pinch lifecycle.

It only reports the raw lifecycle - START (just met), HOLD (still pinched, with
seconds-held), END (just released, with seconds-held). It deliberately does NOT
decide "click vs drag"; that policy lives in the ActionEngine, so the same pinch
could later be remapped to something else entirely.
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
        d = distance(hand.tip(0).xy, hand.tip(1).xy)
        point = hand.tip(1).xy
        pinching = d < ctx.thresholds.pinch

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
