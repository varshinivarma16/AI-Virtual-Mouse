# How It Works

A walk through the internals of the AI Virtual Mouse: what happens to a single
camera frame, what each layer decides, and why the tricky parts are written the
way they are.

The [README](../README.md) covers setup and the gesture cheat-sheet. This document
is for anyone changing the code.

---

## 1. The one-sentence version

Every frame, the app finds your hand, decides **what your hand is doing**, decides
**what that should mean**, and then does it to the real mouse — with smoothing,
because a raw webcam-driven cursor is unusable.

```
Camera ─▶ HandTracker ─▶ GestureEngine ─▶ ActionEngine ─▶ MouseController ─▶ OS
 frame     HandLandmarks   GestureEvent     ActionCommand    (per-platform)
```

The key idea is that **each arrow is a different vocabulary**. The recognition
layer says `PINCH_START` and knows nothing about clicking. The action layer is the
only place that turns `PINCH_START` into `LEFT_CLICK`. That split is what lets you
remap a gesture by editing one file.

---

## 2. The life of a frame

The loop in [main.py](../main.py) is deliberately thin — read a frame, hand it to
the pipeline, show the result, check for `q`:

**Step 1 — Grab and mirror.** `cap.read()` gets a frame. If the read fails, the
loop does *not* quit: webcams routinely drop frames while warming up, so it counts
misses and only gives up after `CAMERA_MAX_MISSES` (30) consecutive failures.
The frame is then flipped horizontally (`cv2.flip`) so moving your hand right moves
the cursor right — without this it feels like a mirror and is unusable.

**Step 2 — Track.** [`Pipeline.process`](../core/pipeline.py) calls
`HandTracker.find_hands()`, which converts the frame to RGB, runs MediaPipe, and
returns a list of `HandLandmarks`. It also draws the hand skeleton onto the frame
as a side effect (that's the preview you see).

**Step 3 — Recognize.** `GestureEngine.process(hands, now, thresholds)` returns
exactly one `GestureEvent` — the winning gesture for this frame, or `IDLE`.

**Step 4 — Decide meaning.** `ActionEngine.process(event, now)` returns an
`ActionCommand`, or `None` if this gesture means nothing right now.

**Step 5 — Execute.** If there's a command, `MouseController.execute(cmd)` maps,
smooths, and drives the real mouse. Each fired action is logged as
`gesture=X -> action=Y`.

**Step 6 — Draw.** The overlay (gesture name, FPS, finger readout, active-region
box) is drawn and the frame is shown.

On exit, `pipeline.shutdown()` runs `release_all()` — a safety net so the left
button can never be left stuck down.

---

## 3. The data model

Two dataclasses and two enums carry everything between layers.
See [core/landmark.py](../core/landmark.py) and [core/gestures.py](../core/gestures.py).

### `Landmark` / `HandLandmarks`

MediaPipe returns 21 points per hand. Rather than pass raw `(x, y)` tuples around,
each point becomes a `Landmark` (x, y in **pixels**, z = relative depth), and each
hand a `HandLandmarks` with a `"Left"`/`"Right"` label.

`HandLandmarks` has three methods that the detectors lean on constantly:

| Method | What it gives you |
|---|---|
| `tip(finger)` | Fingertip landmark, `0..4` = thumb..pinky |
| `palm_size()` | Wrist → middle-knuckle distance, in pixels |
| `fingers_up()` | `[thumb, index, middle, ring, pinky]` as 1/0 |

**`palm_size()` is the most important idea in the codebase.** Raw pixel distances
are meaningless on their own: the same pinch measures ~40px near the camera and
~15px an arm's length back. A fixed pixel threshold that feels right up close
becomes a hair-trigger when you lean back, and the app starts clicking on its own.
The wrist-to-knuckle span is a rigid piece of the palm — it scales with distance
but doesn't change as the fingers move — so dividing by it makes a threshold mean
the same thing at any distance.

`fingers_up()` uses two different rules: the four fingers are "up" when the tip is
**above** its PIP joint (smaller y), while the thumb is judged on **x** and flips
depending on handedness — a thumb never points up, it points sideways.

### `Gesture` vs `Action`

* **`Gesture`** — what the hand is doing: `MOVE`, `PINCH_START/HOLD/END`, `SCROLL`,
  `PALM_HOLD`, `IDLE`. App-agnostic.
* **`Action`** — what the system should do: `MOVE`, `LEFT_CLICK`, `SCROLL`,
  `MEDIA_PLAY_PAUSE`, …

They're enums rather than strings, so a typo is an error instead of a silent
no-op. `GestureEvent` carries the gesture plus an optional cursor `point` and a
scalar `value` (scroll notches, or seconds pinched). `ActionCommand` carries the
action plus `point`/`amount`.

---

## 4. Recognition: one detector per gesture

Each gesture is its own small class implementing `detect(hands, ctx) -> GestureEvent | None`
(see [base_detector.py](../recognition/base_detector.py)). The alternative — one
giant `if/elif` — is what makes gesture code unmaintainable.

`DetectContext` carries `thresholds` and `now`. Time is **passed in rather than
read** inside detectors, which keeps timing logic testable.

### How the engine picks a winner

[`GestureEngine`](../recognition/gesture_engine.py) holds detectors in **priority
order**:

```
FingerScrollDetector  →  HoldDetector  →  PinchDetector  →  MoveDetector
   (highest)                                                  (lowest)
```

Two rules matter here:

1. **The first non-`None` detector wins.** Pinch outranks move, so a click isn't
   overridden by cursor movement.
2. **Every detector still runs, every frame**, even after a winner is found. Their
   internal state (pinch timers, previous positions, swipe anchors) must stay
   current or a detector would "wake up" with stale state the moment it wins.

If nothing matches, the engine returns `GestureEvent(Gesture.IDLE)`.

### The detectors

**`MoveDetector`** — index up, everything else down → cursor follows the index tip.

Its subtlety is the **settle counter**. When you change pose (curling into a pinch,
opening back into a point), the fingers move through intermediate shapes and the
cursor lurches. So it only emits `MOVE` after the pose has been unchanged for
`MOVE_SETTLE_FRAMES` (3) frames — any change resets the counter. The cursor
freezes during the transition, so **the click lands where you aimed**. Pose
stability is judged on the four fingers only; the thumb is too noisy.

**`PinchDetector`** — the thumb+index lifecycle: `PINCH_START` (just met),
`PINCH_HOLD` (still pinched, `value` = seconds), `PINCH_END` (released).

It reports the lifecycle only — it never decides "click vs drag". Two design
points:

* The gap is measured as a **fraction of the palm** (`pinch_ratio`, default 0.22),
  not in pixels — see `palm_size()` above.
* It uses **hysteresis**: starting a pinch needs `gap < 0.22`, but ending one needs
  `gap > 0.22 × 1.6 = 0.352`. With a single threshold, a hand resting near the
  boundary jitters across it and machine-guns clicks.

**`FingerScrollDetector`** — index + middle up, pinky down, swipe vertically.

The peace sign is a **clutch, not the scroll**: holding it still does nothing, and
the wheel follows how far your hand travels. Three details:

* **Ring finger is ignored** — it rarely curls fully in a peace sign, so requiring
  it down made scrolling fail. The **pinky** is what distinguishes this from the
  open-palm pause (all four up).
* **It ratchets.** The first real stroke locks a direction; travel the other way
  is discarded until you drop the pose. On a touchpad you lift your fingers to
  reset — mid-air there's no lift, so the hand you bring back down to flick again
  would otherwise scroll back exactly as far as you just came. Flick-flick-flick to
  keep going one way; to reverse, drop the pose.
* **Idle means "scroll by zero", not `None`.** Because the engine falls through to
  the next detector on `None`, bowing out while paused mid-swipe would let the
  frame reach `PinchDetector` and fire a stray click. A zero-value `SCROLL` says
  *I own this hand, it just isn't moving*.

It tracks the **midpoint** of the two fingertips (steadier than either tip, which
splay as the hand moves), and holds its anchor while inside `SCROLL_DEADZONE` so a
slow deliberate swipe accumulates instead of being discarded frame by frame.

**`HoldDetector`** — four fingers up, held for `HOLD_GESTURE_TIME` (1.0s) → one
`PALM_HOLD`. The thumb is ignored. It fires **once per hold** (`_fired` latch) and
won't fire again until the pose changes.

---

## 5. Action: the one place meaning lives

[`ActionEngine`](../action/action_engine.py) is small on purpose. The full mapping:

| Gesture | Action | Note |
|---|---|---|
| `MOVE` | `MOVE` | pass-through with point |
| `PINCH_START` | `LEFT_CLICK` | fires once when the pinch forms, if debounce allows |
| `PINCH_HOLD` / `PINCH_END` | *(nothing)* | pinch is click-only; holding does nothing |
| `SCROLL` (value ≠ 0) | `SCROLL` | sign decided here |
| `SCROLL` (value = 0) | *(nothing)* | pose held but still |
| `PALM_HOLD` | `MEDIA_PLAY_PAUSE` | |

Two decisions live here and nowhere else:

**Click debounce.** `CLICK_DEBOUNCE` is 0.05s — deliberately *low*. Clicking fires
on `PINCH_START`, and because the debounce is so short, **two quick pinches arrive
at the OS as two rapid clicks, which the OS itself interprets as a double-click.**
There's no double-click gesture; the OS does that work.

**Scroll direction.** The detector reports where the *hand* went (`+` = up). Which
way the *page* moves is a meaning decision, so it's made here:
`SCROLL_NATURAL = True` (default) negates it, giving phone-style behaviour where
swiping up drags the page up toward the next video.

**Because `PINCH_HOLD` outranks `MOVE`,** the cursor is frozen for the whole time
you hold a pinch — the pinch detector owns the hand, so `MoveDetector` never wins.

---

## 6. Execution: mapping, smoothing, scrolling

[`MouseController`](../os_controller/mouse_controller.py) sits above the
platform-specific controller and adds the parts that need screen/camera context.

### Camera → screen

[`CoordinateMapper`](../utils/mapping.py) maps an **inset region** of the camera
frame (`FRAME_MARGIN_X/Y` px from each edge) onto the *full* screen via
`np.interp`, then clamps. The inset is why you don't have to reach the physical
edge of the camera's field of view to hit the corner of your screen — it's the
magenta box in the preview. Bigger margins = smaller active region = less hand
movement covers the whole screen.

### Cursor smoothing

`_place()` does two things, in order:

1. **Dead-zone.** If the new target is within `CURSOR_DEADZONE` (8px) of the
   current position, return the old position unchanged. This is what holds the
   cursor still against hand tremor while you aim — without it the cursor drifts
   off a small button in the moment you go to pinch.
2. **Adaptive exponential smoothing.** `alpha` is interpolated between
   `SMOOTHING_MIN_ALPHA` (0.15) and `SMOOTHING_MAX_ALPHA` (0.5) based on how far
   the target moved, saturating at `SMOOTHING_SPEED_SCALE` (60px). Slow, fine
   moves get smoothed hard (steady enough to click a window's X); fast moves pass
   through with little lag. A single fixed alpha forces you to choose between
   jittery and laggy — this gets both.

### Scroll accumulation

The wheel only moves in **whole notches**, so `_scroll()` banks the fractional
remainder in `_scroll_residual` and carries it to the next frame. Rounding each
frame in isolation would silently discard every swipe under half a notch, and a
slow deliberate swipe would emit `SCROLL` and move nothing.

---

## 7. The OS layer

[`factory.py`](../os_controller/factory.py) picks a controller by
`platform.system()`: Windows → `WindowsController`, Darwin → `MacController`,
anything else → `LinuxController`.

[`BaseOSController`](../os_controller/base_controller.py) implements the primitives
with **pyautogui** (move, click, scroll, media key) and **pynput** (press/release
for drags). Both are cross-platform, so Mac and Linux are literally `pass` — they
inherit everything. Two global settings matter:

* `pyautogui.FAILSAFE = False` — moving into a screen corner would otherwise trip
  the fail-safe and crash. We clamp coordinates in the mapper instead.
* `pyautogui.PAUSE = 0` — pyautogui sleeps 0.1s after *every* call by default,
  which would throttle the entire loop.

### Why Windows scrolling is 60 lines of ctypes

[`WindowsController`](../os_controller/windows_controller.py) reimplements `scroll()`
via **SendInput**, and the reason is worth knowing before you "simplify" it:

1. `pyautogui.scroll()` injects a wheel event that Windows routes to the **focused**
   window — usually the preview window or the terminal, not the page you're
   pointing at.
2. `PostMessageW(WM_MOUSEWHEEL)` targets the window under the cursor, but Chrome,
   Electron apps, and anything with a separate compositor thread **ignore posted
   wheel messages**. The call succeeds and nothing scrolls.
3. **SendInput** injects at the driver level, so the event enters the input queue
   like a physical wheel and Windows delivers it to the window under the cursor
   (the "scroll inactive windows when I hover" setting, on by default since Win10).
   This is what actually scrolls a browser.

The private `ctypes.WinDLL("user32")` handle is also load-bearing:
`ctypes.windll.user32` is a **process-wide singleton** whose function objects are
shared. Setting `.argtypes` on its `SendInput` would rebind the very same object
pynput calls, and pynput's `INPUT` struct would then be rejected against ours —
**breaking every click in the app**. `WinDLL()` builds a separate instance with its
own function cache.

`screen_size()` prefers `screeninfo` and falls back to pyautogui.

---

## 8. Calibration

Pinch size depends on your hand, camera, and seating distance, so
[`calibrator.py`](../calibration/calibrator.py) measures it:

1. Sample the thumb-index distance **as a ratio of palm span** — the same quantity
   the detector compares — over 60 frames while you hold a pinch.
2. Take the **median** (robust against the frames where tracking wobbles).
3. Save `pinch_ratio = clamp(median × 1.5, 0.10, 0.35)` to `calibration.json`.

The ×1.5 gives headroom so a firm pinch reliably fires; the **0.35 cap** is the
important half — too generous a threshold is exactly what makes the app click while
you're merely holding your hand up.

`Thresholds.load()` reads the file on startup and **silently falls back to defaults**
if it's missing or corrupt. `calibration.json` is gitignored — it's per-machine.

---

## 9. Logging

One shared logger, `"virtualmouse"` ([logging_setup.py](../utils/logging_setup.py)):
DEBUG and above to `logs/YYYY-MM-DD.log`, INFO and above to the console. Every
fired action is logged in order, so when a gesture misbehaves, today's log tells
you exactly which gesture won and what it fired.

---

## 10. Tuning guide

Everything lives in [config.py](../config.py). The ones you'll actually touch:

| Symptom | Change |
|---|---|
| Wrong/blank camera | `CAM_INDEX` → 1, 2, … |
| Cursor too jumpy | lower `SMOOTHING_MAX_ALPHA` (~0.4), raise `CURSOR_DEADZONE` |
| Cursor feels laggy | raise `SMOOTHING_MAX_ALPHA`, lower `CURSOR_DEADZONE` |
| Cursor drifts off the button as you click | raise `CURSOR_DEADZONE` (~12) |
| Clicks fire on their own | run `--calibrate`, or lower `Thresholds.pinch_ratio` |
| Clicks won't fire | run `--calibrate`, or raise `pinch_ratio` |
| Can't reach screen edges | lower `FRAME_MARGIN_X/Y` |
| Scrolling too slow/fast | lower/raise `SCROLL_PIXELS_PER_NOTCH` |
| Scroll direction feels backwards | flip `SCROLL_NATURAL` |

---

## 11. Adding a gesture

The layering is designed so this touches four small places and nothing else:

1. **Add the enum members** — `Gesture.X` and `Action.Y` in `core/gestures.py`.
2. **Write the detector** — subclass `BaseDetector` in `recognition/`, return a
   `GestureEvent` when active and `None` otherwise. Measure distances **relative to
   `palm_size()`**, not in pixels. Add hysteresis to anything with a threshold.
3. **Register it** — add to `GestureEngine.detectors` at the right **priority**.
   Remember: if your pose overlaps another gesture's, priority decides who wins,
   and returning `None` hands the frame to the next detector.
4. **Map it** — one `if` in `ActionEngine.process`.

If the OS primitive doesn't exist yet (say, a keyboard shortcut), add it to
`BaseOSController` and handle the action in `MouseController.execute`.

---

## 12. Known gaps and dead code

Documented from reading the source — worth knowing before you go hunting:

* **`DoubleClickDetector` is dead code.** [double_click_detector.py](../recognition/double_click_detector.py)
  is fully written but **not registered** in `GestureEngine`, and its
  `TWO_FINGER_PINCH` gesture is **not handled** by `ActionEngine`. Double-click
  works via two fast pinches + OS interpretation instead (§5).
  `Thresholds.double_click_pinch` exists only to serve this dead detector, and is
  the one threshold still measured in raw pixels.
* **There is no right-click gesture.** The README's architecture section mentions a
  right-click detector and `config.RIGHT_CLICK_HOLD` documents "hold three fingers
  up", but no such detector exists. `Gesture.RIGHT_PINCH`, `Action.RIGHT_CLICK`,
  and `RIGHT_CLICK_HOLD` are all unreferenced. `MouseController` can execute
  `RIGHT_CLICK`; nothing ever emits it.
* **Drag is plumbed but unreachable.** `DRAG_START/MOVE/END` are implemented all
  the way down to `mouse_down()`/`mouse_up()`, but `ActionEngine` never emits them
  (pinch is click-only by design). The plumbing is ready if you want to map it.
* **`paused` is vestigial.** `draw_overlay` takes a `paused` flag, but `Pipeline`
  always passes `False`. `PALM_HOLD` sends a **media key to the OS** — it does not
  pause this app. Nothing ever calls `GestureEngine.reset()` or
  `ActionEngine.reset()`, which were presumably built for that pause feature.
* **README says `max_num_hands=2`**; `config.MAX_HANDS` is actually **1**, and the
  README's "zoom needs two hands" note describes a gesture that doesn't exist.
  Every implemented gesture is one-handed, and all four detectors bail out unless
  `len(hands) == 1`.
* **`MouseController._prev` is passed as the scroll position**, i.e. the last
  *smoothed cursor* spot. On Windows it's ignored anyway (SendInput injects at the
  real cursor); on Mac/Linux pyautogui scrolls at that coordinate.
