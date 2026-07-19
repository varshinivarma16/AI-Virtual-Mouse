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
from utils.logging_setup import get_logger


class TabSwitchDetector(BaseDetector):
    def __init__(self):
        self._start = None         # when the rock pose began (for the open delay)
        self._opened = False       # is the switcher open (Alt held)?
        self._anchor_x = None      # x the current swipe is measured from (camera px)
        self._absent_since = None  # when the pose first went missing (for the grace)
        self._last_step = 0.0      # when the highlight last moved (paces the stepping)
        self._log = get_logger()

    def detect(self, hands: List[HandLandmarks], ctx: DetectContext) -> Optional[GestureEvent]:
        if len(hands) == 1 and self._is_rock(hands[0]):
            return self._pose_held(hands[0], ctx)
        if self._opened and self._absent_since is None:
            # Why the pose was lost, logged once per dropout. A switcher that closes
            # while you're still holding the sign is either the hand vanishing from
            # tracking (motion blur on a fast swipe) or the shape failing - and the
            # two want opposite fixes, so don't guess: look here.
            self._log.debug(
                "tab: pose lost (hands=%d, shape_ok=%s)",
                len(hands),
                self._is_rock(hands[0]) if len(hands) == 1 else "n/a",
            )
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
            if (ctx.now - self._last_step) < config.TAB_STEP_MIN_INTERVAL:
                # Too soon since the last move. Hold the anchor rather than
                # re-anchoring, so this travel isn't thrown away - it lands as a step
                # the moment the interval is up. A fast sweep still crosses several
                # windows, it just does it at a readable pace instead of all at once.
                return GestureEvent(Gesture.TAB_HOLD, hand_label=hand.label)
            self._anchor_x = x
            self._last_step = ctx.now
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
        # Measured along the HAND's own axes, not the screen's. This used to compare
        # raw screen y ("is the tip higher up the image than its knuckle"), which
        # quietly gets stricter the more the hand rotates - and the hand DOES rotate,
        # because sweeping sideways to move the highlight tilts it. Past roughly 70
        # degrees the sign stopped registering mid-swipe and the switcher committed
        # on its own. `fingers_up`/`reach` are angle-independent, so the sign reads
        # the same however you hold it:
        #   * index & pinky EXTENDED
        #   * middle CURLED in
        # The "back" pose fails on the middle finger, which it holds extended.
        fingers = hand.fingers_up()
        middle_curled = hand.reach(2) < config.TAB_MIDDLE_CURL
        upright = hand.uprightness() >= config.TAB_MIN_UPRIGHT
        return bool(fingers[1] and fingers[4]) and middle_curled and upright

    def reset(self):
        self._start = None
        self._opened = False
        self._anchor_x = None
        self._absent_since = None
        self._last_step = 0.0
