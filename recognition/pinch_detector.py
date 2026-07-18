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

A click is the one gesture here that can't be taken back, so START is the strict
end of the lifecycle. Three things gate it, all aimed at the same failure - the
app clicking while you meant to do something else:

  1. POSE. An extended middle finger means you're holding a pose (scroll, peace),
     not pinching. A real thumb+index pinch curls the rest of the hand.
  2. DWELL. The gap must read as closed for several consecutive frames. A single
     frame of MediaPipe noise, or fingers crossing paths as the hand reshapes,
     is not a click.
  3. BLOCKING. While a higher-priority gesture owns the hand, the engine blocks
     this detector. A hand that is already closed when that gesture releases has
     to OPEN and touch again to click - it can't fall out of a scroll into a click.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext
from utils.math_utils import distance


class PinchDetector(BaseDetector):
    def __init__(self):
        self._start = None      # timestamp the current pinch began, or None
        self._closed_frames = 0 # consecutive frames the gap has read as touching
        self._blocked = False   # another gesture owned the hand: no click until fingers reopen

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self.reset()
            return None

        hand = hands[0]
        point = hand.tip(1).xy
        # Thumb-index gap as a fraction of the palm: ~0.1 touching, ~1.0 spread.
        gap = distance(hand.tip(0).xy, hand.tip(1).xy) / hand.palm_size()

        # Hysteresis: it takes a real touch to start a pinch, but a clearly wider
        # gap to end one. With a single threshold, a hand resting near the boundary
        # jitters across it and machine-guns clicks.
        if self._start is None:
            closed = gap < ctx.thresholds.pinch_ratio
        else:
            closed = gap < ctx.thresholds.pinch_ratio * ctx.thresholds.pinch_release

        # An open hand is what clears a block: you have to let go before you can
        # click again. Same threshold the release uses, so it's the same "open".
        if self._blocked:
            if gap >= ctx.thresholds.pinch_ratio * ctx.thresholds.pinch_release:
                self._blocked = False
            else:
                self._closed_frames = 0
                self._start = None
                return None

        # An extended middle finger is a pose, not a pinch. This is what stops a
        # two-finger scroll from ending in a click: even with the thumb resting
        # against the index, the fingers are up, so there's nothing to fire.
        if config.PINCH_REQUIRE_MIDDLE_DOWN and hand.fingers_up()[2]:
            self._closed_frames = 0
            if self._start is not None:
                held = ctx.now - self._start
                self._start = None
                return GestureEvent(Gesture.PINCH_END, point=point, value=held, hand_label=hand.label)
            return None

        if closed:
            self._closed_frames += 1
            if self._start is None:
                # Dwell before firing. The cost is a few ms of latency on a real
                # click; the benefit is that momentary contact - fingers passing
                # each other, a jittery frame - never reaches the OS.
                if self._closed_frames < config.PINCH_CONFIRM_FRAMES:
                    return None
                self._start = ctx.now
                return GestureEvent(Gesture.PINCH_START, point=point, hand_label=hand.label)
            held = ctx.now - self._start
            return GestureEvent(Gesture.PINCH_HOLD, point=point, value=held, hand_label=hand.label)

        # not pinching
        self._closed_frames = 0
        if self._start is not None:
            held = ctx.now - self._start
            self._start = None
            return GestureEvent(Gesture.PINCH_END, point=point, value=held, hand_label=hand.label)
        return None

    def block(self):
        """Another detector owns this frame, so this hand isn't clicking.

        Called by the engine every frame a higher-priority gesture wins. Without
        it, a hand that happens to be closed during a scroll or a fist is already
        'pinching' the moment that gesture lets go, and the release reads as a
        click the user never made. Blocking latches until the fingers open.
        """
        self._blocked = True
        self._closed_frames = 0
        self._start = None

    def reset(self):
        self._start = None
        self._closed_frames = 0
        self._blocked = False
