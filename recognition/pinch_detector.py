"""
PinchDetector: the thumb+index pinch lifecycle.

It only reports the raw lifecycle - START (just met), HOLD (still pinched, with
seconds-held), END (just released, with seconds-held). It deliberately does NOT
decide "click vs drag"; that policy lives in the ActionEngine, so the same pinch
could later be remapped to something else.

The pinch is measured RELATIVE TO THE PALM, not in raw camera pixels. Pixel
distances shrink as the hand moves away from the camera, so a fixed pixel
threshold that feels right up close turns into a hair-trigger further back.
Dividing by the palm span makes the threshold mean the same thing at any distance.

WHY THIS IS FUSSIER THAN "ARE THE TIPS CLOSE"
Tip-to-tip distance alone does not describe a pinch. When a hand relaxes, the
index finger curls into the palm and its tip ends up right beside the thumb tip -
geometrically identical to a pinch, with none of the intent. That is what made
this app click on its own between scroll flicks: on the return stroke, the hand
passes through exactly that shape. So a touch only counts as a pinch when:

  1. REACH. The index is actually extended toward the thumb (tip far from its own
     knuckle), not curled up beside it. This is the one that matters.
  2. POSE. The middle finger isn't extended - that's a scroll/peace pose, not a
     click.
  3. DWELL. The shape holds for several consecutive frames, so a single noisy
     frame can't click.
  4. COOLDOWN. Another gesture owning the hand freezes clicks for a moment after
     it lets go, and the fingers must open before they can pinch again. Gestures
     end by relaxing, and a relaxing hand looks like a pinch.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext
from utils.math_utils import distance


class PinchDetector(BaseDetector):
    def __init__(self):
        self._start = None       # timestamp the current pinch began, or None
        self._closed_frames = 0  # consecutive frames the shape has read as a pinch
        self._blocked_until = 0.0  # no clicks before this time (another gesture had the hand)
        self._needs_open = True    # must see the fingers apart before a click can arm

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) != 1:
            self.reset()
            return None

        hand = hands[0]
        point = hand.tip(1).xy
        # Thumb-index gap as a fraction of the palm: ~0.1 touching, ~1.0 spread.
        gap = distance(hand.tip(0).xy, hand.tip(1).xy) / hand.palm_size()
        open_gap = ctx.thresholds.pinch_ratio * ctx.thresholds.pinch_release

        # Hysteresis: it takes a real touch to start a pinch, but a clearly wider
        # gap to end one. With a single threshold, a hand resting near the boundary
        # jitters across it and machine-guns clicks.
        touching = gap < (open_gap if self._start is not None else ctx.thresholds.pinch_ratio)

        # An extended index is what separates a pinch from a hand that's merely
        # closed. Checked against the finger's own knuckle, so it holds at any hand
        # angle. See the module docstring - this is the fix for the stray clicks.
        reaching = hand.reach(1) >= config.PINCH_MIN_INDEX_REACH

        # An extended middle finger means you're holding a pose (scroll, peace),
        # not clicking.
        posing = config.PINCH_REQUIRE_MIDDLE_DOWN and hand.fingers_up()[2]

        pinching = touching and reaching and not posing

        # A click is the CLOSING of the fingers, so the detector has to have seen
        # them open first. It starts out waiting for that, which is why a hand that
        # wanders into frame already closed - or comes out of another gesture that
        # way - doesn't click until it opens and pinches deliberately.
        if gap >= open_gap:
            self._needs_open = False

        if ctx.now < self._blocked_until or self._needs_open:
            self._closed_frames = 0
            self._start = None
            return None

        if pinching:
            self._closed_frames += 1
            if self._start is None:
                # Dwell before firing. Costs a few ms on a real click; means a
                # momentary contact never reaches the OS.
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

    def block(self, now: float):
        """Another detector owns this frame, so this hand isn't clicking.

        Called by the engine every frame a higher-priority gesture wins. Gestures
        don't end cleanly - you relax out of them, and a relaxing hand passes
        through a pinch-like shape. So owning the hand also buys a short cooldown
        after letting go, and the fingers have to open before a click can arm.
        Without this, the return stroke between two scroll flicks fires a click.
        """
        self._blocked_until = now + config.PINCH_BLOCK_COOLDOWN
        self._needs_open = True
        self._closed_frames = 0
        self._start = None

    def reset(self):
        self._start = None
        self._closed_frames = 0
        self._blocked_until = 0.0
        self._needs_open = True  # a hand that reappears already closed is not a click
