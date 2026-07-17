"""
Pipeline: wires the whole flow together for each frame.

    frame -> HandTracker -> GestureEngine -> ActionEngine -> MouseController
                                                           -> overlay
"""

import time

from action.action_engine import ActionEngine
from config import Thresholds
from os_controller.mouse_controller import MouseController
from recognition.gesture_engine import GestureEngine
from tracking.hand_tracker import HandTracker
from utils.drawing import draw_overlay
from utils.fps import FpsCounter
from utils.logging_setup import get_logger


class Pipeline:
    def __init__(self, cam_w: int, cam_h: int):
        self.tracker = HandTracker()
        self.engine = GestureEngine()
        self.actions = ActionEngine()
        self.mouse = MouseController(cam_w, cam_h)
        self.thresholds = Thresholds.load()
        self.fps = FpsCounter()
        self._log = get_logger()

    def process(self, frame):
        hands = self.tracker.find_hands(frame, draw=True)
        now = time.time()

        event = self.engine.process(hands, now, self.thresholds)
        command = self.actions.process(event, now)

        if command is not None:
            self.mouse.execute(command)
            self._log.info("gesture=%s -> action=%s", event.gesture.name, command.action.name)

        fps = self.fps.tick()
        fingers = hands[0].fingers_up() if hands else None
        draw_overlay(
            frame,
            gesture=event.gesture.name,
            paused=False,
            fps=fps,
            fingers=fingers,
            n_hands=len(hands),
        )
        return frame

    def shutdown(self):
        self.mouse.release_all()
        self._log.info("pipeline shutdown")
