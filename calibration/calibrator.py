"""
Calibrator: measures your pinch distance and saves thresholds to calibration.json.

Different hands, webcams and seating distances make a fixed "pinch = 40px" wrong
for most people. This routine samples the thumb-index distance while you hold a
pinch, takes the median, and derives a threshold a bit above it. Run once with:

    python main.py --calibrate
"""

import statistics

import cv2

import config
from config import Thresholds
from tracking.hand_tracker import HandTracker
from utils.logging_setup import get_logger
from utils.math_utils import distance


def run_calibration(cap, frames: int = 60) -> Thresholds:
    log = get_logger()
    tracker = HandTracker()
    samples = []

    log.info("calibration started")
    print("CALIBRATION: pinch your thumb + index together and hold still...")

    while len(samples) < frames:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        hands = tracker.find_hands(frame, draw=True)
        if len(hands) == 1:
            d = distance(hands[0].tip(0).xy, hands[0].tip(1).xy)
            samples.append(d)

        cv2.putText(
            frame,
            f"CALIBRATE - pinch & hold  {len(samples)}/{frames}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )
        cv2.imshow(config.WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    thresholds = Thresholds.load()
    if samples:
        median = statistics.median(samples)
        # threshold a bit above the measured pinch so a firm pinch reliably fires
        thresholds.pinch = max(20.0, median * 1.8)
        thresholds.double_click_pinch = thresholds.pinch
        thresholds.save()
        log.info("calibration saved: pinch=%.1f (median=%.1f)", thresholds.pinch, median)
        print(f"Saved: pinch threshold = {thresholds.pinch:.1f}px (median pinch {median:.1f}px)")
    else:
        print("No hand detected during calibration - keeping existing thresholds.")
        log.warning("calibration collected no samples")

    return thresholds
