"""
Entry point: open the webcam, build the pipeline, run the loop.

    python main.py              # run the virtual mouse
    python main.py --calibrate  # measure your pinch first, then run

The loop stays deliberately thin - every real decision lives in the pipeline and
the layers below it. Press 'q' in the preview window to quit.
"""

import argparse

import cv2

import config
from calibration.calibrator import run_calibration
from core.pipeline import Pipeline
from utils.logging_setup import setup_logging


def open_camera():
    cap = cv2.VideoCapture(config.CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
    return cap


def main():
    parser = argparse.ArgumentParser(description="AI Virtual Mouse (hand gestures)")
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="measure your pinch distance and save thresholds before running",
    )
    args = parser.parse_args()

    log = setup_logging()
    cap = open_camera()
    if not cap.isOpened():
        log.error("could not open camera index %s (try changing CAM_INDEX in config.py)", config.CAM_INDEX)
        return

    if args.calibrate:
        run_calibration(cap)

    pipeline = Pipeline(config.CAM_WIDTH, config.CAM_HEIGHT)
    log.info("virtual mouse started - press 'q' in the window to quit")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                log.warning("failed to read frame from camera")
                break
            frame = cv2.flip(frame, 1)  # mirror so movement feels natural
            frame = pipeline.process(frame)
            cv2.imshow(config.WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        pipeline.shutdown()
        cap.release()
        cv2.destroyAllWindows()
        log.info("virtual mouse stopped")


if __name__ == "__main__":
    main()
