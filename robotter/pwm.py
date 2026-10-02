"""PWM output boundary. Hardware drivers belong behind this interface."""

from collections import defaultdict
from typing import Protocol


class PwmOutput(Protocol):
    def set_pulse_us(self, channel: int, pulse_us: int) -> None:
        """Set a channel's PWM pulse width in microseconds."""


class MemoryPwm:
    """In-memory PWM backend for tests and command development; drives no hardware."""

    def __init__(self) -> None:
        self.pulses: dict[int, int] = {}
        self.history: dict[int, list[int]] = defaultdict(list)

    def set_pulse_us(self, channel: int, pulse_us: int) -> None:
        self.pulses[channel] = pulse_us
        self.history[channel].append(pulse_us)
