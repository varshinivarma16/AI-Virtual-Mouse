"""
GestureEngine: runs every detector each frame and picks one winning gesture.

All detectors run every frame so their internal state (pinch timers, previous
positions) stays current even when another gesture wins. The winner is chosen by
priority - the detector order in `self.detectors`, highest first. Scroll and hold
gestures outrank the pointer gestures; pinch outranks move so a click doesn't get
overridden by cursor movement.
"""

from typing import List

from core.gestures import Gesture, GestureEvent
from core.landmark import HandLandmarks
from recognition.base_detector import DetectContext
from recognition.hold_detector import HoldDetector
from recognition.move_detector import MoveDetector
from recognition.pinch_detector import PinchDetector
from recognition.finger_scroll_detector import FingerScrollDetector
from recognition.swipe_left_detector import SwipeLeftDetector
from recognition.fist_detector import FistDetector
from recognition.tab_switch_detector import TabSwitchDetector


class GestureEngine:
    def __init__(self):
        # Highest priority first. TabSwitch is first so that once a switch is open
        # it owns the hand until it commits - otherwise relaxing the hand curls it
        # through a fist, FistDetector would win that frame and swallow TAB_COMMIT,
        # and Alt would be left stuck down. It stays quiet (returns None) whenever no
        # switch is active, so the fist guarantee below is unaffected. FistDetector
        # is next so a closed hand strictly blocks every other gesture (notably a
        # stray pinch-click). The pointer gestures follow; none of their poses
        # overlap (fist = all curled, tab = index+pinky up, swipe = fingers
        # horizontal, scroll = fingers up).
        self.detectors = [
            TabSwitchDetector(),
            FistDetector(),
            SwipeLeftDetector(),
            FingerScrollDetector(),
            HoldDetector(),
            PinchDetector(),
            MoveDetector(),
        ]

    def process(self, hands: List[HandLandmarks], now: float, thresholds) -> GestureEvent:
        ctx = DetectContext(thresholds=thresholds, now=now)
        winner = None
        for detector in self.detectors:  # already in priority order
            event = detector.detect(hands, ctx)
            if event is not None and winner is None:
                winner = event  # keep first (highest priority), but keep running
                # the rest so their state stays fresh
        return winner if winner is not None else GestureEvent(Gesture.IDLE)

    def reset(self):
        for detector in self.detectors:
            detector.reset()
