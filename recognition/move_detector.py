"""
MoveDetector: index finger up (and the other fingers down) => cursor-follow.

To keep the cursor from lurching while you change hand pose - e.g. curling into a
thumbs-up to click, or opening back into a point - it only emits MOVE once the
pointing pose has been held steady for MOVE_SETTLE_FRAMES frames. Any change in
which fingers are up resets that counter, so the cursor freezes at its last spot
during the transition between gestures and the click lands where you aimed.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext


class MoveDetector(BaseDetector):
    def __init__(self):
        self._prev_pose = None  # last frame's [index..pinky] up/down (thumb ignored)
        self._stable = 0        # consecutive frames the pose has been unchanged

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self._prev_pose = None
            self._stable = 0
            return None

        hand = hands[0]
        fingers = hand.fingers_up()
        # Thumb is noisy (and it swings out for the thumbs-up click), so judge pose
        # stability on the four fingers only.
        pose = tuple(fingers[1:])
        if pose == self._prev_pose:
            self._stable += 1
        else:
            self._stable = 0
            self._prev_pose = pose

        # Only a clean index-point drives the cursor.
        if not (fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]):
            return None

        # Freeze for the first few frames of a fresh/steadying pose so the
        # transition to or from a thumbs-up click doesn't drag the cursor.
        if self._stable < config.MOVE_SETTLE_FRAMES:
            return None

        return GestureEvent(Gesture.MOVE, point=hand.tip(1).xy, hand_label=hand.label)

    def reset(self):
        self._prev_pose = None
        self._stable = 0
