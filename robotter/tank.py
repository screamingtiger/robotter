"""High-level, fail-safe two-track motion primitives."""

from collections.abc import Callable
from time import sleep as system_sleep

from .config import TankConfig
from .esc import Esc
from .pwm import PwmOutput
from .track import Track


class TankDrive:
    def __init__(
        self,
        pwm: PwmOutput,
        config: TankConfig = TankConfig(),
        sleep: Callable[[float], None] = system_sleep,
    ) -> None:
        self._config = config
        self._sleep = sleep
        self.left = Track(Esc(pwm, config.left_channel, config.esc), config.left_direction)
        self.right = Track(Esc(pwm, config.right_channel, config.esc), config.right_direction)

    def arm(self) -> None:
        self.left.arm(self._sleep)
        self.right.arm(self._sleep)
        self.stop()

    def stop(self) -> None:
        self.left.stop()
        self.right.stop()

    def forward(self, speed: float) -> None:
        self._check_speed(speed)
        self.left.set_speed(speed)
        self.right.set_speed(speed)

    def reverse(self, speed: float) -> None:
        self.forward(-speed)

    def pivot_left(self, speed: float) -> None:
        self._check_speed(speed)
        self.left.set_speed(-speed)
        self.right.set_speed(speed)

    def pivot_right(self, speed: float) -> None:
        self._check_speed(speed)
        self.left.set_speed(speed)
        self.right.set_speed(-speed)

    def turn_left_90(self) -> None:
        self._timed_pivot(self.pivot_left)

    def turn_right_90(self) -> None:
        self._timed_pivot(self.pivot_right)

    def _timed_pivot(self, pivot: Callable[[float], None]) -> None:
        try:
            pivot(1.0)
            self._sleep(self._config.turn_90_seconds)
        finally:
            self.stop()

    @staticmethod
    def _check_speed(speed: float) -> None:
        if not 0.0 <= speed <= 1.0:
            raise ValueError("command speed must be between 0.0 and 1.0")
