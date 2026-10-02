"""Linux-side client for the Arduino Q real-time tank controller.

This module sends motion intent through Arduino Router Bridge.  It never
creates Linux GPIO PWM; all ESC pulses remain owned by the STM32U585 firmware.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Event, RLock, Thread
from time import sleep
from typing import Any


class RtTankClient:
    """Fail-safe proxy for the RT MCU tank controller.

    Continuous commands are repeated while active.  If this process stops,
    the MCU's independent command watchdog sends both ESCs to neutral.
    """

    def __init__(
        self,
        bridge: Any | None = None,
        *,
        turn_90_seconds: float = 0.75,
        heartbeat_period_s: float | None = 0.10,
        sleep_fn: Callable[[float], None] = sleep,
    ) -> None:
        if turn_90_seconds <= 0:
            raise ValueError("turn_90_seconds must be positive")
        if heartbeat_period_s is not None and heartbeat_period_s <= 0:
            raise ValueError("heartbeat_period_s must be positive or None")
        self._bridge = bridge
        self._turn_90_seconds = turn_90_seconds
        self._heartbeat_period_s = heartbeat_period_s
        self._sleep = sleep_fn
        self._desired = (0.0, 0.0)
        self._lock = RLock()
        self._stop_event = Event()
        self._heartbeat: Thread | None = None
        self._connected = False

    def connect(self, timeout_s: float = 5.0) -> None:
        """Connect to the local Arduino Router service and start heartbeats."""
        with self._lock:
            if self._connected:
                return
            if self._bridge is None:
                try:
                    from arduino.router_bridge import Bridge
                except ImportError as error:
                    raise RuntimeError(
                        "arduino-router-bridge is required; install the project's RT dependency"
                    ) from error
                self._bridge = Bridge()
            self._bridge.connect(timeout=timeout_s)
            self._connected = True
            self._stop_event.clear()
            if self._heartbeat_period_s is not None:
                self._heartbeat = Thread(target=self._heartbeat_loop, daemon=True)
                self._heartbeat.start()

    def arm(self) -> None:
        self._call("tank.arm")

    def stop(self) -> None:
        with self._lock:
            self._desired = (0.0, 0.0)
            self._call("tank.stop")

    def forward(self, speed: float) -> None:
        self._set_tracks(speed, speed)

    def reverse(self, speed: float) -> None:
        self._set_tracks(-speed, -speed)

    def pivot_left(self, speed: float) -> None:
        self._set_tracks(-speed, speed)

    def pivot_right(self, speed: float) -> None:
        self._set_tracks(speed, -speed)

    def turn_left_90(self) -> None:
        self._pivot_timed(-1.0, 1.0)

    def turn_right_90(self) -> None:
        self._pivot_timed(1.0, -1.0)

    def close(self) -> None:
        """Request neutral, stop the heartbeat, and release the bridge client."""
        try:
            if self._connected:
                self.stop()
        finally:
            self._stop_event.set()
            if self._heartbeat is not None:
                self._heartbeat.join(timeout=1.0)
            bridge = self._bridge
            if bridge is not None and hasattr(bridge, "disconnect"):
                bridge.disconnect()
            self._connected = False

    def _set_tracks(self, left: float, right: float) -> None:
        self._check_speed(left)
        self._check_speed(right)
        with self._lock:
            self._call("tank.set_tracks", left, right)
            self._desired = (left, right)

    def _pivot_timed(self, left: float, right: float) -> None:
        with self._lock:
            self._desired = (0.0, 0.0)
            self._call("tank.pivot_timed", left, right, round(self._turn_90_seconds * 1000))

    def _heartbeat_loop(self) -> None:
        assert self._heartbeat_period_s is not None
        while not self._stop_event.wait(self._heartbeat_period_s):
            with self._lock:
                if not self._connected or self._desired == (0.0, 0.0):
                    continue
                try:
                    self._call("tank.set_tracks", *self._desired)
                except Exception:
                    # The MCU watchdog is the final safety boundary.  Stop
                    # retrying motion commands if the transport fails.
                    self._desired = (0.0, 0.0)

    def _call(self, method: str, *args: object) -> Any:
        if not self._connected or self._bridge is None:
            raise RuntimeError("RT bridge is not connected")
        result = self._bridge.call(method, *args, timeout=5)
        if result is False:
            raise RuntimeError(f"RT controller rejected {method}")
        return result

    @staticmethod
    def _check_speed(speed: float) -> None:
        if not 0.0 <= speed <= 1.0:
            raise ValueError("command speed must be between 0.0 and 1.0")
