"""Linux-side client for the RT-controlled camera turret servo."""

from __future__ import annotations

from typing import Any


class TurretClient:
    """Command a camera turret relative to its calibrated forward centre."""

    maximum_degrees = 60.0

    def __init__(self, bridge: Any | None = None) -> None:
        self._bridge = bridge
        self._connected = False

    def connect(self, timeout_s: float = 5.0) -> None:
        if self._connected:
            return
        if self._bridge is None:
            try:
                from arduino.router_bridge import Bridge
            except ImportError as error:
                raise RuntimeError("arduino-router-bridge is required for turret control") from error
            self._bridge = Bridge()
        self._bridge.connect(timeout=timeout_s)
        self._connected = True

    def center(self) -> None:
        self._call("turret.center")

    def set_angle_degrees(self, angle_degrees: float) -> None:
        if not -self.maximum_degrees <= angle_degrees <= self.maximum_degrees:
            raise ValueError(
                f"turret angle must be between {-self.maximum_degrees:g} and {self.maximum_degrees:g} degrees"
            )
        self._call("turret.set_angle", angle_degrees)

    def close(self) -> None:
        if self._connected:
            try:
                self.center()
            finally:
                if self._bridge is not None and hasattr(self._bridge, "disconnect"):
                    self._bridge.disconnect()
                self._connected = False

    def _call(self, method: str, *arguments: object) -> Any:
        if not self._connected or self._bridge is None:
            raise RuntimeError("turret bridge is not connected")
        result = self._bridge.call(method, *arguments, timeout=5)
        if result is False:
            raise RuntimeError(f"RT controller rejected {method}")
        return result
