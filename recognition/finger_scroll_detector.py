"""
FingerScrollDetector: hold two fingers up (index + middle) to scroll up.

Raise the index and middle fingers - the "peace sign" - and the page scrolls up a
step every frame the pose is held. Only up-scroll is mapped.

The ring finger is deliberately IGNORED: it rarely curls all the way in a peace
sign, so requiring it down made scrolling fail (the hand read as three fingers).
What matters is index + middle up and the pinky down - the pinky is what separates
this from the open-palm pause (all four fingers up).
"""

from typing import List, Optional

from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext


class FingerScrollDetector(BaseDetector):
    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            return None

        fingers = hands[0].fingers_up()
        # index + middle up, pinky down (thumb and ring ignored).
        if fingers[1] and fingers[2] and not fingers[4]:
            return GestureEvent(Gesture.SCROLL, value=1.0, hand_label=hands[0].label)
        return None

    def reset(self):
        pass
