"""
TabSwitchDetector: the rock sign 🤘 drives the Alt+Tab window switcher.

Unlike the other gestures, this one is a *held mode*: the switcher stays open (the
OS keeps Alt pressed) for as long as you hold the pose, mirroring how you'd hold Alt
on the keyboard. The lifecycle:

  * Hold the rock sign (index + pinky up, middle down) for TAB_OPEN_TIME
        -> TAB_OPEN     (OS presses Alt down + taps Tab; the switcher appears)
  * Keep holding and swipe the hand right / left
        -> TAB_NEXT / TAB_PREV   (Tab / Shift+Tab; the highlight moves)
  * Keep holding but still
        -> TAB_HOLD     (owns the hand, does nothing)
  * Drop the pose
        -> TAB_COMMIT   (OS releases Alt; the highlighted window comes forward)

The pinky is the discriminator: the scroll pose needs the pinky DOWN, so a pinky-up
rock sign can never be confused with it (the ring finger, which reads unreliably, is
ignored here just as it is in the scroll detector).

While the switcher is open the detector always returns a non-None event, so it OWNS
the hand - a stray None would let the frame fall through and fire a click mid-switch.
Dropping the pose commits only after a short grace (TAB_RELEASE_GRACE) so a one-frame
tracking blip doesn't select the wrong window early. Everything horizontal is
measured relative to `palm_size()` so it holds at any distance from the camera.
"""

from typing import List, Optional

import config
from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import BaseDetector, DetectContext


class TabSwitchDetector(BaseDetector):
    def __init__(self):
        self._start = None         # when the rock pose began (for the open delay)
        self._opened = False       # is the switcher open (Alt held)?
        self._anchor_x = None      # x the current swipe is measured from (camera px)
        self._absent_since = None  # when the pose first went missing (for the grace)

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) == 1 and self._is_rock(hands[0]):
            return self._pose_held(hands[0], ctx)
        return self._pose_gone(ctx)

    def _pose_held(self, hand: HandLandmarks, ctx: DetectContext) -> GestureEvent:
        self._absent_since = None
        x = (hand.tip(1).x + hand.tip(4).x) / 2.0  # midpoint of index & pinky tips

        if not self._opened:
            if self._start is None:
                self._start = ctx.now
            if (ctx.now - self._start) >= config.TAB_OPEN_TIME:
                self._opened = True
                self._anchor_x = x
                return GestureEvent(Gesture.TAB_OPEN, hand_label=hand.label)
            return GestureEvent(Gesture.TAB_HOLD, hand_label=hand.label)  # arming; own the hand

        # Switcher open: horizontal travel moves the highlight. Screen is mirrored,
        # so hand-right = larger x = next window (matches Tab's forward direction).
        step = config.TAB_SWIPE_RATIO * hand.palm_size()
        dx = x - self._anchor_x
        if abs(dx) >= step:
            self._anchor_x = x
            gesture = Gesture.TAB_NEXT if dx > 0 else Gesture.TAB_PREV
            return GestureEvent(gesture, hand_label=hand.label)
        return GestureEvent(Gesture.TAB_HOLD, hand_label=hand.label)  # holding; own the hand

    def _pose_gone(self, ctx: DetectContext) -> Optional[GestureEvent]:
        if not self._opened:
            self.reset()
            return None  # never opened -> let other detectors have the frame

        if self._absent_since is None:
            self._absent_since = ctx.now
        if (ctx.now - self._absent_since) >= config.TAB_RELEASE_GRACE:
            self.reset()
            return GestureEvent(Gesture.TAB_COMMIT)
        return GestureEvent(Gesture.TAB_HOLD)  # within grace: own the hand, don't commit yet

    @staticmethod
    def _is_rock(hand: HandLandmarks) -> bool:
        f = hand.fingers_up()
        # index + pinky up, middle down. Ring ignored (unreliable), thumb ignored.
        return bool(f[1] and f[4] and not f[2])

    def reset(self):
        self._start = None
        self._opened = False
        self._anchor_x = None
        self._absent_since = None
