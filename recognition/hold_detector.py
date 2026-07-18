"""
HoldDetector: an open hand (four fingers up) held for HOLD_GESTURE_TIME.

The thumb is ignored (its up/down reading is unreliable), so this fires whether or
not the thumb is spread - four fingers up is enough. It is distinct from the
two-finger scroll, so there's no ambiguity. Fires PALM_HOLD (mapped to pause/resume)
once per hold, then waits for the pose to change before it can fire again.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext


class HoldDetector(BaseDetector):
    def __init__(self):
        self._holding = False  # is an open palm currently held?
        self._start = None     # when the palm pose began
        self._fired = False    # have we already fired for this hold?

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self.reset()
            return None

        hand = hands[0]
        fingers = hand.fingers_up()
        four_up = fingers[1] and fingers[2] and fingers[3] and fingers[4]
        # An open palm means "stop" only when it's actually held UP. fingers_up is
        # angle-independent by design, so without this an open hand lying sideways
        # (a natural resting or mid-transition posture) reads as a palm and toggles
        # your media after a second.
        upright = hand.uprightness() >= config.PALM_MIN_UPRIGHT
        if not (four_up and upright):
            self.reset()
            return None

        if not self._holding:
            self._holding = True
            self._start = ctx.now
            self._fired = False
            return None

        if not self._fired and (ctx.now - self._start) >= config.HOLD_GESTURE_TIME:
            self._fired = True
            return GestureEvent(Gesture.PALM_HOLD)
        return None

    def reset(self):
        self._holding = False
        self._start = None
        self._fired = False
