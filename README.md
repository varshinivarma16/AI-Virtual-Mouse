# AI Virtual Mouse — Hand Gesture Recognition

Control your mouse with hand gestures through a webcam, using **MediaPipe** hand
tracking and **OpenCV**. Move the cursor, click, scroll, and play/pause videos —
all with your hand.

## Architecture

The project is built as a one-directional pipeline with each concern in its own layer:

```
Camera ─▶ HandTracker ─▶ GestureEngine ─▶ ActionEngine ─▶ MouseController ─▶ OS
 frame     Landmarks       GestureEvent      ActionCommand    (per-platform)
```

- **`tracking/`** — `HandTracker` wraps MediaPipe and returns typed `HandLandmarks`
  (x, y, **z**, visibility). The only module that imports mediapipe.
- **`core/`** — domain types: `Landmark`, `Gesture`/`Action` **enums** (no magic
  strings), `GestureEvent`, `ActionCommand`, and the `Pipeline` orchestrator.
- **`recognition/`** — one small detector per gesture (move, pinch, right-click,
  two-finger scroll, hold), combined by `GestureEngine` by priority.
  Detectors only describe *what the hand is doing*.
- **`action/`** — `ActionEngine` decides what a gesture *means* (e.g.
  `PINCH_END → LEFT_CLICK`). This is the one place to remap gestures.
- **`os_controller/`** — `BaseOSController` + `Windows/Linux/Mac` subclasses behind
  a `factory`, plus the `MouseController` facade (mapping + smoothing).
- **`utils/`** — geometry, camera→screen mapping, FPS, overlay drawing, logging.
- **`calibration/`** — measures your pinch distance and saves `calibration.json`.

```
AI-Virtual-Mouse/
├── main.py
├── config.py
├── requirements.txt
├── core/         landmark.py  gestures.py  pipeline.py
├── tracking/     hand_tracker.py
├── recognition/  base_detector.py  *_detector.py  gesture_engine.py
├── action/       action_engine.py
├── os_controller/ base_controller.py  windows_controller.py  linux_controller.py  mac_controller.py  factory.py  mouse_controller.py
├── calibration/  calibrator.py
├── utils/        math_utils.py  mapping.py  fps.py  drawing.py  logging_setup.py
└── logs/         (auto-created, date-stamped .log files)
```

## Setup

Requires **Python 3.9–3.11** (MediaPipe has limited support on 3.12+).

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python main.py                 # start the virtual mouse
python main.py --calibrate     # measure your pinch first (recommended once), then run
```

A preview window opens showing your hand skeleton, the active region box, the
current gesture, and FPS. Press **`q`** to quit.

## Gesture cheat-sheet

| Gesture (one hand)                           | Action                    |
|----------------------------------------------|---------------------------|
| ☝️ Index finger up only                       | **Move** cursor (smoothed)|
| 🤏 Pinch **thumb + index**                     | **Left click**            |
| 🤏🤏 **Two quick pinches**                     | **Double click**          |
| ✌️ **Two fingers up** (index + middle)         | **Scroll up**             |
| ✋ **Open hand** (four fingers up), hold ~1s   | **Pause / play the video** (media key) |

The cursor **freezes while you change pose**, so a click lands where you aimed
(tune with `MOVE_SETTLE_FRAMES` in `config.py`).

## Calibration

Pinch size in pixels depends on your hand, camera and distance. `--calibrate`
samples your thumb-index distance while you hold a pinch, takes the median, and
writes tuned thresholds to `calibration.json`, which the app loads on startup.

## Logging

Everything is logged to `logs/YYYY-MM-DD.log` (and INFO+ to the console). If a
gesture misbehaves, open today's log to see exactly which gesture and action fired.

## Configuration

All tunables live in `config.py`:

- `CAM_INDEX` — change if the wrong camera opens (try 1, 2, …).
- `SMOOTHING_MIN_ALPHA` / `SMOOTHING_MAX_ALPHA` — lower = smoother, higher = snappier
  (min applies to slow fine moves, max to fast moves).
- `CURSOR_DEADZONE` — how still the cursor holds against hand tremor when aiming;
  raise it if the cursor drifts off small buttons, lower it for finer control.
- `FRAME_MARGIN_X/Y` — size of the active region mapped to the screen (bigger
  margins = smaller, more central region = easier to reach the screen edges).
- `CLICK_DEBOUNCE`, `RIGHT_CLICK_HOLD`, `HOLD_GESTURE_TIME` — gesture timing.
- `Thresholds` — pinch distance (overridden by calibration).

## Troubleshooting

- **Wrong/blank camera** → change `CAM_INDEX` in `config.py`.
- **Cursor too jumpy** → lower `SMOOTHING_MAX_ALPHA` (e.g. 0.4) and/or raise `CURSOR_DEADZONE`.
- **Cursor drifts off a button while clicking** → raise `CURSOR_DEADZONE` (e.g. 12).
- **Cursor feels laggy** → raise `SMOOTHING_MAX_ALPHA` and/or lower `CURSOR_DEADZONE`.
- **Clicks not firing / firing too easily** → run `--calibrate`, or tune
  `Thresholds.pinch` in `config.py`.
- **Poor detection** → improve lighting and use a plainer background.
- **Install fails on `mediapipe`** → make sure you're on Python 3.9–3.11.

## Notes

- Cursor **smoothing** is built into movement (a raw virtual mouse is unusable
  without it).
- **Zoom needs two hands**; MediaPipe is set to `max_num_hands=2`.
- Extending is easy: add a detector in `recognition/`, register it in
  `GestureEngine`, add the `Gesture`/`Action` enum members, and map it in
  `ActionEngine` — no other layer needs to change.
```
