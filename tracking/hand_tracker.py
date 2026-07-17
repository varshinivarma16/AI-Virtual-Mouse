"""
HandTracker: the boundary between MediaPipe and the rest of the app.

It is the ONLY module that imports mediapipe. It converts each detected hand into
a `HandLandmarks` (pixel x/y + relative z + handedness) and optionally draws the
skeleton onto the frame for the preview window. Everything downstream works with
our typed model, not raw MediaPipe protobufs.
"""

import cv2
import mediapipe as mp

import config
from core.landmark import HandLandmarks, Landmark


class HandTracker:
    def __init__(self):
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_HANDS,
            min_detection_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )

    def find_hands(self, frame, draw: bool = True):
        """Return a list of HandLandmarks for the hands visible in `frame`."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)

        hands = []
        if results.multi_hand_landmarks:
            h, w = frame.shape[:2]
            handedness = results.multi_handedness or []
            for idx, hand_lms in enumerate(results.multi_hand_landmarks):
                points = [
                    Landmark(
                        x=lm.x * w,
                        y=lm.y * h,
                        z=lm.z,
                        visibility=getattr(lm, "visibility", 1.0),
                    )
                    for lm in hand_lms.landmark
                ]
                label = "Right"
                if idx < len(handedness):
                    label = handedness[idx].classification[0].label
                hands.append(HandLandmarks(points=points, label=label))

                if draw:
                    self._mp_draw.draw_landmarks(
                        frame, hand_lms, self._mp_hands.HAND_CONNECTIONS
                    )
        return hands
