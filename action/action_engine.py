"""
ActionEngine: the single place that decides what a gesture MEANS.

This is the layer you'd edit to remap gestures (e.g. make a gesture play/pause
music instead of clicking). It owns the click debounce, so the detectors can stay
purely about hand shape.

  PINCH_START (thumb+index)       -> LEFT_CLICK   (click only; no drag)
  SCROLL (two fingers swiped)     -> SCROLL        pass-through with payload
  MOVE                            -> pass-through with payload
  PALM_HOLD (open hand)           -> MEDIA_PLAY_PAUSE  (pause/play the video)
  SWIPE_LEFT (two fingers <-)      -> NAVIGATE_BACK     (OS Back; fires once per pose)
  TAB_OPEN/NEXT/PREV/COMMIT (rock) -> ALT_TAB_*         (held window switcher)
"""

from typing import Optional

import config
from core.gestures import Action, ActionCommand, Gesture, GestureEvent


class ActionEngine:
    def __init__(self):
        self._last_click = 0.0

    def _can_click(self, now: float) -> bool:
        return (now - self._last_click) >= config.CLICK_DEBOUNCE

    def _mark_click(self, now: float):
        self._last_click = now

    def process(self, event: GestureEvent, now: float) -> Optional[ActionCommand]:
        g = event.gesture

        if g == Gesture.MOVE:
            return ActionCommand(Action.MOVE, point=event.point)

        # Pinch is click-only: fire once when the pinch forms. Holding does nothing;
        # two quick pinches land as an OS double-click.
        if g == Gesture.PINCH_START and self._can_click(now):
            self._mark_click(now)
            return ActionCommand(Action.LEFT_CLICK)

        if g == Gesture.SCROLL:
            # value == 0 means the scroll pose is held but still. The detector sends
            # it to keep ownership of the hand; there's nothing for the OS to do.
            if event.value == 0.0:
                return None
            # The detector reports where the HAND went (+ = up). Which way the PAGE
            # should go is a meaning decision, so it's made here.
            amount = -event.value if config.SCROLL_NATURAL else event.value
            return ActionCommand(Action.SCROLL, amount=amount)

        if g == Gesture.PALM_HOLD:
            return ActionCommand(Action.MEDIA_PLAY_PAUSE)

        if g == Gesture.SWIPE_LEFT:
            # value == 0.0 means the pose is held but already fired; the detector
            # sends it to keep the hand, but there's nothing more to do.
            if event.value == 0.0:
                return None
            return ActionCommand(Action.NAVIGATE_BACK)

        # Alt+Tab window switcher. TAB_HOLD only exists to keep the hand while the
        # switcher is open/arming, so it maps to nothing.
        if g == Gesture.TAB_OPEN:
            return ActionCommand(Action.ALT_TAB_OPEN)
        if g == Gesture.TAB_NEXT:
            return ActionCommand(Action.ALT_TAB_NEXT)
        if g == Gesture.TAB_PREV:
            return ActionCommand(Action.ALT_TAB_PREV)
        if g == Gesture.TAB_COMMIT:
            return ActionCommand(Action.ALT_TAB_COMMIT)

        return None

    def reset(self):
        self._last_click = 0.0
