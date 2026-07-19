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
# Finger up/down reading
# ---------------------------------------------------------------------------
# Fingers are judged along the HAND's own axes (wrist -> knuckles), never the
# screen's, so a pose reads the same upright, tilted, or fully sideways. See
# HandLandmarks._axes for why that matters.
FINGER_EXTEND_MARGIN = 0.05   # how far past its PIP joint a fingertip must reach, as a
                              # fraction of palm span, to count as extended (small
                              # dead-band so a borderline finger doesn't flicker)

# ---------------------------------------------------------------------------
# Active frame region -> screen mapping (pixel margins from each camera edge)
# ---------------------------------------------------------------------------
# The magenta box is the active region: it maps onto the whole screen. Each edge
# has its OWN margin, so you can move the box to wherever your hand rests, not just
# the centre. Smaller margin = that edge sits closer to the frame border.
#   - Hand rests LOW?  -> big TOP, tiny BOTTOM (box sits low, current setup).
#   - Hand rests high? -> tiny TOP, big BOTTOM.
FRAME_MARGIN_LEFT = 80
FRAME_MARGIN_RIGHT = 80
FRAME_MARGIN_TOP = 100
FRAME_MARGIN_BOTTOM = 10

# Cursor reach / gain. The box maps onto the screen, so normally your fingertip has
# to touch a box EDGE to put the cursor on a screen edge - and the far corners of a
# big box sit past a comfortable reach, so the cursor never gets there. Sensitivity
# amplifies movement around the box CENTRE: at 1.3, covering the inner ~77% of the
# box already sweeps the whole screen, so you hit every edge and corner with room to
# spare. Raise it if the corners are still hard to reach; 1.0 = plain edge-to-edge.
CURSOR_SENSITIVITY = 1.3

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

# ---------------------------------------------------------------------------
# Click strictness (thumb+index pinch)
# ---------------------------------------------------------------------------
# A click is the one destructive gesture here - a wrong scroll is invisible, a wrong
# click opens something. So the pinch is deliberately harder to trigger than it is
# to recognise: it must look like a pinch, hold that shape, and not be the tail end
# of some other gesture.
PINCH_CONFIRM_FRAMES = 2      # consecutive frames the fingers must read as touching
                              # before a click fires (a 1-frame tracking blip is not a click)
PINCH_REQUIRE_MIDDLE_DOWN = True  # middle finger extended = you're posing (scroll/peace),
                              # not clicking. Set False if you pinch with the middle up.
PINCH_MIN_INDEX_REACH = 0.75  # index tip must sit this far from its own knuckle (in palm
                              # spans) for a touch to count as a pinch. THE important one:
                              # a relaxed hand curls the index tip down NEXT TO the thumb,
                              # so tip-to-tip distance alone reads a resting hand as a
                              # pinch. A deliberate pinch reaches the index out (~1.0+);
                              # a curled one measures ~0.5.
PINCH_BLOCK_COOLDOWN = 0.45   # seconds after another gesture owns the hand during which no
                              # click can fire. Covers the return stroke between scroll
                              # flicks, where the hand passes through pinch-like shapes on
                              # its way back up.
RIGHT_CLICK_HOLD = 0.3        # hold three fingers up this long to right-click
HOLD_GESTURE_TIME = 1.0       # open-palm hold time to toggle pause
PALM_MIN_UPRIGHT = 0.6        # how upright the open palm must be to count (1.0 = fingers
                              # straight up, 0.0 = sideways); 0.6 allows ~50 degrees of
                              # tilt. Without this, a hand lying sideways with the
                              # fingers open reads as a palm and toggles your media.

# ---------------------------------------------------------------------------
# Scrolling (two fingers up, swiped vertically)
# ---------------------------------------------------------------------------
# Holding the pose does nothing; the wheel follows how far the hand travels.
SCROLL_NATURAL = True          # True: swipe up = drag the page up = go to the NEXT
                               # video/post (phone-style). False: swipe up scrolls up.
SCROLL_DEADZONE = 6.0          # px of vertical travel before a swipe counts (kills tremor)
SCROLL_PIXELS_PER_NOTCH = 12.0 # px of hand travel per wheel notch (lower = more scroll per swipe)
SCROLL_MULTIPLIER = 1          # overall gain on the result (raise = faster)
SCROLL_RELEASE_GRACE = 0.2     # seconds the scroll pose may flicker out before releasing the hand
                               # (bridges mid-swipe flickers so they don't fall through to a stray click)

# ---------------------------------------------------------------------------
# "Back" gesture (index + middle held horizontal, pointing left)
# ---------------------------------------------------------------------------
# All palm-relative (fractions of wrist->knuckle span) so they hold at any distance.
SWIPE_MIN_EXTEND = 0.55    # index/middle tip must be this far LEFT of its knuckle to count as pointing left
SWIPE_MAX_VERTICAL = 1.0   # |vertical|/|horizontal| below this = the finger is horizontal-ish (allows a diagonal tilt)
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
TAB_OPEN_TIME = 0.12       # seconds the rock sign must be held before the switcher opens.
                           # Short on purpose: the switcher should appear as soon as you
                           # show the sign. The pose is distinctive enough that it doesn't
                           # need a long confirmation.
TAB_SWIPE_RATIO = 0.6      # horizontal hand travel (as a fraction of palm span) to move one
                           # window. Bigger = each window needs a more deliberate sweep.
TAB_STEP_MIN_INTERVAL = 0.18  # min seconds between highlight moves. Hand travel decides HOW
                           # FAR you go; this stops a fast sweep from firing several Tabs in
                           # the same instant, faster than the switcher can redraw or you can
                           # read it. Travel made during the wait is kept, not discarded.
TAB_RELEASE_GRACE = 0.45   # seconds the pose may vanish before committing. Was 0.15 (~4
                           # frames), which a fast sideways swipe blows straight through:
                           # motion blur makes MediaPipe drop the hand for a few frames and
                           # the switcher committed while the sign was still being held.
TAB_MIN_UPRIGHT = 0.2      # how upright the hand must be (1.0 = fingers straight up, 0.0 =
                           # sideways). Generous - it only rules out a hand lying on its
                           # side; the rock sign itself now reads at any tilt.
TAB_MIDDLE_CURL = 0.6      # middle fingertip within this * palm of its knuckle = curled in (rules out the extended-middle "back" pose)

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
