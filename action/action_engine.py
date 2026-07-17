"""
ActionEngine: the single place that decides what a gesture MEANS.

This is the layer you'd edit to remap gestures (e.g. make a gesture play/pause
music instead of clicking). It owns the click debounce, so the detectors can stay
purely about hand shape.

  PINCH_START (thumb+index)       -> LEFT_CLICK   (click only; no drag)
  SCROLL (two fingers up)         -> SCROLL        pass-through with payload
  MOVE                            -> pass-through with payload
  PALM_HOLD (open hand)           -> MEDIA_PLAY_PAUSE  (pause/play the video)
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
            return ActionCommand(Action.SCROLL, amount=event.value)

        if g == Gesture.PALM_HOLD:
            return ActionCommand(Action.MEDIA_PLAY_PAUSE)

        return None

    def reset(self):
        self._last_click = 0.0
