"""Configuration for bidirectional ESCs and a two-track tank."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EscCalibration:
    """PWM values for one bidirectional ESC, expressed in microseconds."""

    neutral_us: int = 1500
    forward_us: int = 2000
    reverse_us: int = 1000
    arm_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not self.reverse_us < self.neutral_us < self.forward_us:
            raise ValueError("reverse < neutral < forward PWM values are required")
        if self.arm_seconds < 0:
            raise ValueError("arm_seconds cannot be negative")

    def pulse_for(self, speed: float) -> int:
        """Map a normalized speed in [-1.0, 1.0] to an ESC pulse width."""
        if not -1.0 <= speed <= 1.0:
            raise ValueError("speed must be between -1.0 and 1.0")
        if speed >= 0:
            return round(self.neutral_us + speed * (self.forward_us - self.neutral_us))
        return round(self.neutral_us + speed * (self.neutral_us - self.reverse_us))


@dataclass(frozen=True)
class TankConfig:
    """Physical configuration. Tune only after validating the real ESCs."""

    left_channel: int = 0
    right_channel: int = 1
    left_direction: int = 1
    right_direction: int = 1
    turn_90_seconds: float = 0.75
    esc: EscCalibration = EscCalibration()

    def __post_init__(self) -> None:
        if self.left_direction not in (-1, 1) or self.right_direction not in (-1, 1):
            raise ValueError("track directions must be 1 or -1")
        if self.turn_90_seconds <= 0:
            raise ValueError("turn_90_seconds must be positive")
