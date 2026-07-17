"""
DoubleClickDetector: index and middle both up, tips brought together.

Edge-triggered like the right-click detector: one DOUBLE_CLICK per pinch-together,
reset when the fingers separate.
"""

from typing import List, Optional

from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext
from utils.math_utils import distance


class DoubleClickDetector(BaseDetector):
    def __init__(self):
        self._active = False

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self._active = False
            return None

        hand = hands[0]
        fingers = hand.fingers_up()
        if fingers[1] and fingers[2]:
            d = distance(hand.tip(1).xy, hand.tip(2).xy)
            if d < ctx.thresholds.double_click_pinch:
                if not self._active:
                    self._active = True
                    return GestureEvent(
                        Gesture.TWO_FINGER_PINCH, point=hand.tip(1).xy, hand_label=hand.label
                    )
                return None
            self._active = False
        else:
            self._active = False
        return None

    def reset(self):
        self._active = False
