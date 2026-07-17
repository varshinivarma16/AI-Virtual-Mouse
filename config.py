"""
Static configuration + calibratable thresholds.

Two kinds of settings live here:
  1. Fixed constants (camera, smoothing, timing, paths) - edit directly.
  2. `Thresholds` - the pinch distance that depends on your hand,
     webcam and distance from the screen. These can be measured automatically by
     `python main.py --calibrate`, which writes calibration.json. On startup the
     app loads calibration.json if present and falls back to the defaults below.
"""

import json
import os
from dataclasses import asdict, dataclass

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
CAM_INDEX = 0
CAM_WIDTH = 640
CAM_HEIGHT = 480

# ---------------------------------------------------------------------------
# MediaPipe hand detection
# ---------------------------------------------------------------------------
MAX_HANDS = 1                 # all gestures are one-handed
DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.6

# ---------------------------------------------------------------------------
# Active frame region -> screen mapping (pixel margins from each camera edge)
# ---------------------------------------------------------------------------
FRAME_MARGIN_X = 170
FRAME_MARGIN_Y = 120

# ---------------------------------------------------------------------------
# Cursor movement / smoothing
# ---------------------------------------------------------------------------
# The cursor uses *adaptive* exponential smoothing plus a small jitter dead-zone.
# Slow, fine hand moves are smoothed hard so the cursor sits still enough to click
# a tiny target (e.g. a window's X); fast moves pass through with little lag.
CURSOR_DEADZONE = 8.0         # px: hold the cursor still when the target moves less than this (kills hand tremor while aiming)
SMOOTHING_MIN_ALPHA = 0.15    # slow/fine moves -> steadier cursor (lower = smoother)
SMOOTHING_MAX_ALPHA = 0.5     # fast moves -> snappier cursor (higher = more responsive)
SMOOTHING_SPEED_SCALE = 60.0  # px of target travel at which smoothing reaches MAX_ALPHA
MOVE_SETTLE_FRAMES = 3        # freeze the cursor for this many frames after the hand pose
                              # changes, so switching between pointing and a thumbs-up
                              # click doesn't drag the cursor off target

# ---------------------------------------------------------------------------
# Timing (seconds)
# ---------------------------------------------------------------------------
CLICK_DEBOUNCE = 0.05         # min interval between clicks (low, so two quick pinches double-click)
RIGHT_CLICK_HOLD = 0.3        # hold three fingers up this long to right-click
HOLD_GESTURE_TIME = 1.0       # open-palm hold time to toggle pause

# ---------------------------------------------------------------------------
# Output multipliers (raw gesture value -> OS units)
# ---------------------------------------------------------------------------
SCROLL_MULTIPLIER = 1         # scroll "clicks" per frame while two fingers are held up (raise = faster)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(__file__)
CALIBRATION_FILE = os.path.join(_ROOT, "calibration.json")

# ---------------------------------------------------------------------------
# UI overlay
# ---------------------------------------------------------------------------
SHOW_FPS = True
SHOW_REGION = True
WINDOW_NAME = "AI Virtual Mouse"


@dataclass
class Thresholds:
    """Distance thresholds (in camera pixels) that calibration can tune."""

    pinch: float = 40.0               # thumb+finger closer than this = a pinch (click)
    double_click_pinch: float = 40.0  # index+middle tips this close = double-click pose

    def save(self, path=CALIBRATION_FILE):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path=CALIBRATION_FILE):
        t = cls()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(t, key):
                        setattr(t, key, float(value))
            except (ValueError, OSError):
                pass  # corrupt file -> silently fall back to defaults
        return t
