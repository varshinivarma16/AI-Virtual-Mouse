"""
The two vocabularies that keep recognition and action-generation separate.

  * `Gesture`  - what the HAND is doing (raw, app-agnostic). Produced by the
                 recognition layer. A PINCH_START says nothing about clicking.
  * `Action`   - what the SYSTEM should do. Produced by the action layer, which
                 is the single place that decides "PINCH_END -> LEFT_CLICK".

Because they're enums (not strings) you get autocomplete and no typo bugs, and
you can later remap a gesture to a different action (e.g. PINCH -> play/pause
music) by editing only the action layer.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple


class Gesture(Enum):
    IDLE = auto()
    MOVE = auto()               # index up only -> carries point
    PINCH_START = auto()        # thumb+index just met
    PINCH_HOLD = auto()         # thumb+index held -> value = seconds held
    PINCH_END = auto()          # thumb+index released -> value = seconds held
    RIGHT_PINCH = auto()        # thumb+middle met (edge-triggered)
    TWO_FINGER_PINCH = auto()   # index+middle tips together (edge-triggered)
    SCROLL = auto()             # two fingers up (index+middle) swiped vertically ->
                                # value = notches of HAND travel, signed (+ = hand up).
                                # The action layer decides which way the page moves.
    PALM_HOLD = auto()          # open hand (four fingers up) held -> pause the video


class Action(Enum):
    NONE = auto()
    MOVE = auto()
    LEFT_CLICK = auto()
    RIGHT_CLICK = auto()
    DOUBLE_CLICK = auto()
    SCROLL = auto()
    DRAG_START = auto()
    DRAG_MOVE = auto()
    DRAG_END = auto()
    MEDIA_PLAY_PAUSE = auto()   # press the OS media key (pause/play a video)


@dataclass
class GestureEvent:
    """A recognised gesture with an optional cursor point and scalar payload."""

    gesture: Gesture
    point: Optional[Tuple[float, float]] = None
    value: float = 0.0          # signed scroll notches (+ = hand up) or pinch-held seconds
    hand_label: str = ""


@dataclass
class ActionCommand:
    """A concrete instruction for the OS controller to execute."""

    action: Action
    point: Optional[Tuple[float, float]] = None
    amount: float = 0.0
