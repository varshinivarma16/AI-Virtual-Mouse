"""
Typed hand-landmark model.

MediaPipe returns x, y, z (and, for some solutions, visibility) per point. Instead
of passing raw (x, y) tuples around and throwing away depth, we wrap each point in
a `Landmark` and each hand in a `HandLandmarks`. Keeping `z` lets later gestures
use depth (e.g. distinguishing a pinch toward the camera from one across it).
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# MediaPipe landmark indices, ordered [thumb, index, middle, ring, pinky].
TIP_IDS = [4, 8, 12, 16, 20]
PIP_IDS = [3, 6, 10, 14, 18]


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

    def fingers_up(self) -> List[int]:
        """
        Return [thumb, index, middle, ring, pinky] as 1 (up) / 0 (down).

        Four fingers: tip above its PIP joint (smaller y) => up.
        Thumb: uses x and flips with handedness.
        """
        up = []
        if self.label == "Right":
            up.append(1 if self.points[TIP_IDS[0]].x > self.points[PIP_IDS[0]].x else 0)
        else:
            up.append(1 if self.points[TIP_IDS[0]].x < self.points[PIP_IDS[0]].x else 0)
        for i in range(1, 5):
            up.append(1 if self.points[TIP_IDS[i]].y < self.points[PIP_IDS[i]].y else 0)
        return up
