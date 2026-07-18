"""
Typed hand-landmark model.

MediaPipe returns x, y, z (and, for some solutions, visibility) per point. Instead
of passing raw (x, y) tuples around and throwing away depth, we wrap each point in
a `Landmark` and each hand in a `HandLandmarks`. Keeping `z` lets later gestures
use depth (e.g. distinguishing a pinch toward the camera from one across it).
"""

from dataclasses import dataclass, field
from typing import List, Tuple

import config

# MediaPipe landmark indices, ordered [thumb, index, middle, ring, pinky].
TIP_IDS = [4, 8, 12, 16, 20]
PIP_IDS = [3, 6, 10, 14, 18]
MCP_IDS = [2, 5, 9, 13, 17]  # knuckle at the base of each finger

_WRIST_ID = 0
_MIDDLE_MCP_ID = 9  # knuckle at the base of the middle finger


@dataclass
class Landmark:
    """A single hand point. x/y are in pixels; z is MediaPipe's relative depth."""

    x: float
    y: float
    z: float = 0.0
    # MediaPipe Hands does not emit visibility (only Pose does); kept at 1.0 for
    # a uniform API so downstream code can rely on the field existing.
    visibility: float = 1.0

    @property
    def xy(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class HandLandmarks:
    """21 landmarks for one hand plus its handedness label."""

    points: List[Landmark] = field(default_factory=list)
    label: str = "Right"  # "Left" | "Right"

    def __getitem__(self, i: int) -> Landmark:
        return self.points[i]

    def __len__(self) -> int:
        return len(self.points)

    def tip(self, finger: int) -> Landmark:
        """Fingertip landmark for finger 0..4 (thumb..pinky)."""
        return self.points[TIP_IDS[finger]]

    def mcp(self, finger: int) -> Landmark:
        """Knuckle landmark for finger 0..4 (thumb..pinky)."""
        return self.points[MCP_IDS[finger]]

    def reach(self, finger: int) -> float:
        """How far a fingertip sits from its own knuckle, in palm spans.

        This is how STRAIGHT a finger is, independent of which way the hand points:
        ~1.2 fully extended, ~0.5 curled into the palm. `fingers_up` answers a
        different question - which side of its PIP the tip is on - and a half-curled
        finger can pass that while being nowhere near extended.
        """
        tip, knuckle = self.tip(finger), self.mcp(finger)
        d = ((tip.x - knuckle.x) ** 2 + (tip.y - knuckle.y) ** 2) ** 0.5
        return d / self.palm_size()

    def palm_size(self) -> float:
        """Wrist-to-middle-knuckle distance, in camera pixels.

        A yardstick for turning pixel distances into hand-relative ones. Raw pixels
        are meaningless on their own: the same pinch measures ~40px near the camera
        and ~15px an arm's length back, so a fixed pixel threshold silently becomes
        a hair-trigger as you lean away. This span is a rigid bit of palm, so it
        scales with distance while staying fixed as the fingers move.
        """
        wrist = self.points[_WRIST_ID]
        mcp = self.points[_MIDDLE_MCP_ID]
        size = ((wrist.x - mcp.x) ** 2 + (wrist.y - mcp.y) ** 2) ** 0.5
        return max(size, 1e-6)  # never divide by zero on a degenerate hand

    def _axes(self):
        """The hand's OWN (up, side) unit vectors.

        `up` runs wrist -> middle knuckle: the direction the fingers extend when the
        hand opens, at whatever angle the hand happens to be held. `side` is that
        turned 90 degrees, pointing the way the thumb sticks out (it flips with
        handedness, since a left thumb points the opposite way from a right one).

        Measuring against these instead of the screen's axes is what lets a pose
        survive a tilted or sideways hand. "Tip is higher on screen than its knuckle"
        only means "finger is extended" while the hand is upright - turn the hand on
        its side and extended fingers start reading as curled, which is how the
        sideways Back pose used to get mistaken for other gestures.
        """
        wrist, mcp = self.points[_WRIST_ID], self.points[_MIDDLE_MCP_ID]
        ux, uy = mcp.x - wrist.x, mcp.y - wrist.y
        length = max((ux * ux + uy * uy) ** 0.5, 1e-6)  # never normalise a zero vector
        ux, uy = ux / length, uy / length
        if self.label == "Right":
            return (ux, uy), (-uy, ux)
        return (ux, uy), (uy, -ux)

    def uprightness(self) -> float:
        """How upright the hand is: 1.0 = fingers point straight up, 0.0 = fully
        sideways, -1.0 = pointing straight down.

        `fingers_up` deliberately ignores hand angle so a pose reads the same however
        you hold it. That's right for recognising the SHAPE, but some gestures also
        care about the ORIENTATION - an open palm means "stop" only when it's held
        up, not when your hand happens to be lying sideways. This is how those
        gestures ask.
        """
        (_, uy), _ = self._axes()
        return -uy  # screen y grows downward, so "up" is negative y

    def fingers_up(self) -> List[int]:
        """
        Return [thumb, index, middle, ring, pinky] as 1 (extended) / 0 (curled).

        Each finger counts as extended when its tip reaches past its PIP joint along
        the hand's own axis (see `_axes`): the four fingers along `up`, the thumb
        along `side` - a thumb never points "up", it points sideways. Because the
        axes come from the hand itself, the reading is the same whether the hand is
        upright, tilted, or fully on its side.
        """
        up_axis, side_axis = self._axes()
        margin = config.FINGER_EXTEND_MARGIN * self.palm_size()

        def extended(finger: int, axis) -> int:
            tip, pip = self.points[TIP_IDS[finger]], self.points[PIP_IDS[finger]]
            reach = (tip.x - pip.x) * axis[0] + (tip.y - pip.y) * axis[1]
            return 1 if reach > margin else 0

        return [extended(0, side_axis)] + [extended(i, up_axis) for i in range(1, 5)]
