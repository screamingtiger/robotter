"""One explicitly armed bidirectional electronic speed controller."""

from collections.abc import Callable

from .config import EscCalibration
from .pwm import PwmOutput


class Esc:
    def __init__(self, pwm: PwmOutput, channel: int, calibration: EscCalibration) -> None:
        self._pwm = pwm
        self._channel = channel
        self._calibration = calibration
        self._armed = False

    @property
    def armed(self) -> bool:
        return self._armed

    def arm(self, sleep: Callable[[float], None]) -> None:
        """Send neutral PWM for the ESC's configured arming interval."""
        self.stop()
        sleep(self._calibration.arm_seconds)
        self._armed = True

    def set_speed(self, speed: float) -> None:
        if not self._armed:
            raise RuntimeError("ESC is not armed; send ARM before movement")
        self._pwm.set_pulse_us(self._channel, self._calibration.pulse_for(speed))

    def stop(self) -> None:
        """Neutral is always safe to send, even before arming."""
        self._pwm.set_pulse_us(self._channel, self._calibration.neutral_us)
