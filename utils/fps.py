"""A tiny frame-rate counter for the on-screen overlay."""

import time


class FpsCounter:
    def __init__(self):
        self._prev = time.time()
        self.fps = 0.0

    def tick(self) -> float:
        now = time.time()
        dt = now - self._prev
        self._prev = now
        if dt > 0:
            self.fps = 1.0 / dt
        return self.fps
