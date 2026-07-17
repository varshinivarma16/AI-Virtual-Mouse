"""
FingerScrollDetector: hold two fingers up (index + middle) and swipe to scroll.

The peace sign is the *clutch*, not the scroll itself: holding it still does
nothing. While it's held, vertical hand travel drives the wheel, and the page
moves by the distance you swept.

It ratchets: the first real stroke of a hold locks the direction, and travel the
other way is ignored until you drop the pose. A touchpad doesn't need this because
you lift your fingers to reset - mid-air there's no lift, so the hand you bring
back down to flick again would otherwise scroll back exactly as far as you just
came. Locking means you can flick-flick-flick to keep going one way; to reverse,
drop the pose and start a new hold.

The ring finger is deliberately IGNORED: it rarely curls all the way in a peace
sign, so requiring it down made scrolling fail (the hand read as three fingers).
What matters is index + middle up and the pinky down - the pinky is what separates
this from the open-palm pause (all four fingers up).
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext


class FingerScrollDetector(BaseDetector):
    def __init__(self):
        self._anchor_y = None  # y the current swipe is measured from (camera px)
        self._locked_dir = 0   # +1 up / -1 down: direction this hold is ratcheting

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self.reset()
            return None

        hand = hands[0]
        fingers = hand.fingers_up()
        # index + middle up, pinky down (thumb and ring ignored).
        if not (fingers[1] and fingers[2] and not fingers[4]):
            self.reset()
            return None

        # Track the midpoint of the two raised fingertips: steadier than either tip
        # alone, since the fingers splay slightly as the hand moves.
        y = (hand.tip(1).y + hand.tip(2).y) / 2.0

        if self._anchor_y is None:
            self._anchor_y = y  # first frame of the pose: just arm the swipe
            return self._idle(hand)

        # Camera y grows downward, so moving the hand UP means a smaller y.
        dy = self._anchor_y - y
        if abs(dy) < config.SCROLL_DEADZONE:
            # Below the dead-zone: hold the anchor so a slow, deliberate swipe
            # accumulates into a scroll instead of being discarded frame by frame.
            return self._idle(hand)

        direction = 1 if dy > 0 else -1
        if self._locked_dir == 0:
            self._locked_dir = direction  # first real stroke picks the direction

        if direction != self._locked_dir:
            # The return stroke. You have to bring your hand back down before you
            # can flick up again, and there's no way to "lift off" mid-air the way
            # you would off a touchpad - so without this, the way back scrolls an
            # equal amount the other way and cancels the flick you just made.
            # Re-anchor so the return travel is discarded, not banked.
            self._anchor_y = y
            return self._idle(hand)

        self._anchor_y = y
        notches = dy / config.SCROLL_PIXELS_PER_NOTCH
        return GestureEvent(Gesture.SCROLL, value=notches, hand_label=hand.label)

    @staticmethod
    def _idle(hand: HandLandmarks) -> GestureEvent:
        """Pose held but not moving: scroll by zero.

        This claims the hand rather than returning None. The engine hands the frame
        to the next detector when one returns None, so bowing out here would let a
        pause mid-swipe fall through to the pinch detector and fire a stray click.
        A zero-value SCROLL says "I own this hand, it just isn't moving yet".
        """
        return GestureEvent(Gesture.SCROLL, value=0.0, hand_label=hand.label)

    def reset(self):
        self._anchor_y = None
        self._locked_dir = 0  # dropping the pose is what frees the direction again
