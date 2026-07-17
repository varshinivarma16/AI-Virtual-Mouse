"""
SwipeLeftDetector: index + middle held horizontal, pointing LEFT -> "Back".

The pose is a sideways peace sign: index and middle fingers extended and aimed to
the left of the screen. The ring and pinky just have to NOT also point left (they
can be curled or sticking up). It's the horizontal cousin of the scroll pose
(index+middle *up*), so the two never both match - one is vertical, the other
horizontal. The "pointing left" test keys on the index/middle *direction*, which is
what separates it from the rock sign and scroll (both point up).

Like HoldDetector, the pose must be HELD for `SWIPE_HOLD_TIME` before it fires, so
a split-second flash of horizontal fingers doesn't trigger Back. It then fires ONCE
and stays quiet until you drop the pose. Throughout (both the wait and after firing)
it returns a zero-value event so it *owns* the hand - a None here would fall through
to pinch/move and misfire.

Everything is measured RELATIVE TO THE PALM (`palm_size()`), not in pixels, so the
thresholds hold whether your hand is near the camera or an arm's length back.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext

# MediaPipe landmark ids: (tip, knuckle/MCP) for each finger.
_INDEX = (8, 5)
_MIDDLE = (12, 9)
_RING = (16, 13)
_PINKY = (20, 17)


def _vec(hand: HandLandmarks, tip_id: int, mcp_id: int):
    """Vector from a finger's knuckle to its tip, in camera pixels."""
    tip, mcp = hand.points[tip_id], hand.points[mcp_id]
    return tip.x - mcp.x, tip.y - mcp.y


class SwipeLeftDetector(BaseDetector):
    def __init__(self):
        self._start = None   # when the current pose began, or None
        self._fired = False  # already fired for this hold?

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self.reset()
            return None

        hand = hands[0]
        if not self._is_pose(hand):
            self.reset()
            return None

        if self._start is None:
            self._start = ctx.now  # first frame of the pose: start the clock

        # Own the hand for the whole pose (waiting or already fired) so the frame
        # doesn't fall through to pinch/move and misfire.
        held_long_enough = (ctx.now - self._start) >= config.SWIPE_HOLD_TIME
        if self._fired or not held_long_enough:
            return GestureEvent(Gesture.SWIPE_LEFT, value=0.0, hand_label=hand.label)

        self._fired = True
        return GestureEvent(
            Gesture.SWIPE_LEFT, point=hand.tip(1).xy, value=1.0, hand_label=hand.label
        )

    @staticmethod
    def _is_pose(hand: HandLandmarks) -> bool:
        palm = hand.palm_size()

        def points_left(finger) -> bool:
            dx, dy = _vec(hand, *finger)
            # The preview is mirrored, so "left on screen" is a smaller x (dx < 0).
            far_enough = dx < -config.SWIPE_MIN_EXTEND * palm
            horizontal = abs(dy) < config.SWIPE_MAX_VERTICAL * abs(dx)
            return far_enough and horizontal

        if not (points_left(_INDEX) and points_left(_MIDDLE)):
            return False

        # Ring & pinky must NOT also be aimed left, or a flat open hand pointing left
        # would match too. They're free to be curled OR sticking up - only a finger
        # extended left as far as the pointing ones disqualifies the pose.
        def not_pointing_left(finger) -> bool:
            dx, _ = _vec(hand, *finger)
            return dx > -config.SWIPE_MIN_EXTEND * palm

        return not_pointing_left(_RING) and not_pointing_left(_PINKY)

    def reset(self):
        self._start = None
        self._fired = False  # dropping the pose re-arms the next Back
