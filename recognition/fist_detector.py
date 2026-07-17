"""
FistDetector: a closed fist means STRICTLY no action.

A fist is every finger curled in - each fingertip sitting close to its own knuckle.
When it sees one, it claims the hand with an IDLE event. Because it runs FIRST in
the engine and the engine keeps the first non-None result, that IDLE wins and every
lower detector is ignored for the frame. Without it, a fist's thumb and index tips
sit close together and the PinchDetector reads that as a pinch and fires a stray
click.

It only matches when the INDEX is curled too, so it never swallows a real pinch:
in a pinch the index stays extended (tip far from its knuckle) to meet the thumb.

Curl is measured RELATIVE TO THE PALM (`palm_size()`) so it holds at any distance.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext

# (tip, knuckle/MCP) ids for index, middle, ring, pinky. Thumb is ignored.
_FINGERS = ((8, 5), (12, 9), (16, 13), (20, 17))


class FistDetector(BaseDetector):
    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            return None

        hand = hands[0]
        palm = hand.palm_size()
        for tip_id, mcp_id in _FINGERS:
            tip, mcp = hand.points[tip_id], hand.points[mcp_id]
            reach = ((tip.x - mcp.x) ** 2 + (tip.y - mcp.y) ** 2) ** 0.5
            if reach >= config.FIST_CURL_MAX * palm:
                return None  # a finger is extended -> not a fist

        # All fingers curled: claim the hand so nothing below can fire.
        return GestureEvent(Gesture.IDLE, hand_label=hand.label)
