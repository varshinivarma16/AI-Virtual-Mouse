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
CAMERA_MAX_MISSES = 30  # consecutive failed frame reads before giving up (cameras
                        # drop a few while warming up; don't quit on the first one)

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
# Scrolling (two fingers up, swiped vertically)
# ---------------------------------------------------------------------------
# Holding the pose does nothing; the wheel follows how far the hand travels.
SCROLL_NATURAL = True          # True: swipe up = drag the page up = go to the NEXT
                               # video/post (phone-style). False: swipe up scrolls up.
SCROLL_DEADZONE = 6.0          # px of vertical travel before a swipe counts (kills tremor)
SCROLL_PIXELS_PER_NOTCH = 12.0 # px of hand travel per wheel notch (lower = more scroll per swipe)
SCROLL_MULTIPLIER = 1          # overall gain on the result (raise = faster)

# ---------------------------------------------------------------------------
# "Back" gesture (index + middle held horizontal, pointing left)
# ---------------------------------------------------------------------------
# All palm-relative (fractions of wrist->knuckle span) so they hold at any distance.
SWIPE_MIN_EXTEND = 0.55    # index/middle tip must be this far LEFT of its knuckle to count as pointing left
SWIPE_MAX_VERTICAL = 0.8   # |vertical|/|horizontal| below this = the finger is horizontal, not up/down
SWIPE_CURL_MAX = 0.75      # ring & pinky tip within this of their knuckle = curled (keeps a flat open hand out)
SWIPE_HOLD_TIME = 0.5      # seconds the pose must be held before Back fires (stops a split-second flash from triggering)

# ---------------------------------------------------------------------------
# Fist (all fingers closed) -> strictly no action
# ---------------------------------------------------------------------------
FIST_CURL_MAX = 0.6        # every fingertip within this * palm of its knuckle = a fist; blocks all gestures (incl. a stray pinch-click)

# ---------------------------------------------------------------------------
# Alt+Tab window switcher (rock sign: index + pinky up, middle down)
# ---------------------------------------------------------------------------
# Hold the rock sign to open the switcher (Alt stays held); swipe left/right to move
# the highlight; drop the pose to select. Distances are palm-relative.
TAB_OPEN_TIME = 0.3        # seconds the rock sign must be held before the switcher opens
TAB_SWIPE_RATIO = 0.5      # horizontal hand travel (as a fraction of palm span) to move one window
TAB_RELEASE_GRACE = 0.15   # seconds the pose may vanish before committing (absorbs tracking blips so a flicker doesn't select early)

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
    """Pinch thresholds that calibration can tune.

    `pinch_ratio` is a FRACTION OF THE PALM, not a pixel count, so it holds up as
    you lean toward or away from the camera. See PinchDetector for why.
    """

    pinch_ratio: float = 0.22         # thumb-index gap (/ palm span) that counts as touching
    pinch_release: float = 1.6        # multiple of pinch_ratio the gap must exceed to un-pinch
    double_click_pinch: float = 40.0  # index+middle tips this close (px) = double-click pose

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
