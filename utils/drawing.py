"""On-screen overlay: active region box, current gesture / paused state, FPS."""

import cv2

import config


def draw_overlay(frame, gesture: str, paused: bool, fps: float, fingers=None, n_hands: int = 0):
    h, w = frame.shape[:2]

    if config.SHOW_REGION:
        cv2.rectangle(
            frame,
            (config.FRAME_MARGIN_LEFT, config.FRAME_MARGIN_TOP),
            (w - config.FRAME_MARGIN_RIGHT, h - config.FRAME_MARGIN_BOTTOM),
            (255, 0, 255),
            2,
        )

    label = "PAUSED" if paused else gesture
    color = (0, 0, 255) if paused else (0, 255, 0)
    cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if config.SHOW_FPS:
        cv2.putText(
            frame,
            f"FPS:{fps:.0f}",
            (w - 130, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )

    # Live finger-up debug: T I M R P = thumb, index, middle, ring, pinky (1=up).
    if fingers is not None:
        readout = "  ".join(
            f"{name}:{val}" for name, val in zip("TIMRP", fingers)
        )
        cv2.putText(frame, readout, (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 255), 2)
    hands_txt = f"hands:{n_hands}"
    cv2.putText(frame, hands_txt, (20, 70), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (200, 200, 200), 2)
