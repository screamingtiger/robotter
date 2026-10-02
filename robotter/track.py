"""One tank track driven by one ESC."""

from .esc import Esc


class Track:
    def __init__(self, esc: Esc, direction: int = 1) -> None:
        if direction not in (-1, 1):
            raise ValueError("direction must be 1 or -1")
        self._esc = esc
        self._direction = direction

    def arm(self, sleep) -> None:
        self._esc.arm(sleep)

    def set_speed(self, speed: float) -> None:
        self._esc.set_speed(speed * self._direction)

    def stop(self) -> None:
        self._esc.stop()
