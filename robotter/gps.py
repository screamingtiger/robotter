"""Reusable client, parser, and movement estimate for the RT GPS endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any


@dataclass(frozen=True)
class GpsFix:
    valid: bool
    latitude: float
    longitude: float
    speed_kph: float
    course_degrees: float
    satellites: int
    hdop: float
    altitude_m: float
    age_ms: int


@dataclass(frozen=True)
class MovementObservation:
    moving: bool | None
    distance_since_previous_m: float | None


class GpsClient:
    """Retrieve parsed NMEA navigation fixes from the STM32 RT controller."""

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
                raise RuntimeError("arduino-router-bridge is required for GPS access") from error
            self._bridge = Bridge()
        self._bridge.connect(timeout=timeout_s)
        self._connected = True

    def snapshot(self) -> GpsFix:
        if not self._connected or self._bridge is None:
            raise RuntimeError("GPS bridge is not connected")
        value = self._bridge.call("gps.snapshot", timeout=5)
        if not isinstance(value, str):
            raise RuntimeError("RT GPS endpoint returned an invalid snapshot")
        return parse_snapshot(value)

    def close(self) -> None:
        if self._bridge is not None and hasattr(self._bridge, "disconnect"):
            self._bridge.disconnect()
        self._connected = False


def parse_snapshot(value: str) -> GpsFix:
    """Decode the compact pipe-delimited snapshot returned by the RT MCU."""
    fields = value.split("|")
    if len(fields) != 9 or fields[0] not in {"0", "1"}:
        raise ValueError(f"malformed GPS snapshot: {value!r}")
    try:
        return GpsFix(
            valid=fields[0] == "1",
            latitude=float(fields[1]),
            longitude=float(fields[2]),
            speed_kph=float(fields[3]),
            course_degrees=float(fields[4]),
            satellites=int(fields[5]),
            hdop=float(fields[6]),
            altitude_m=float(fields[7]),
            age_ms=int(fields[8]),
        )
    except ValueError as error:
        raise ValueError(f"malformed GPS snapshot: {value!r}") from error


class MovementVerifier:
    """Estimate whether the tank is moving, without claiming body orientation."""

    def __init__(self, *, minimum_speed_kph: float = 0.36, minimum_distance_m: float = 0.30) -> None:
        self._minimum_speed_kph = minimum_speed_kph
        self._minimum_distance_m = minimum_distance_m
        self._previous: GpsFix | None = None

    def observe(self, fix: GpsFix) -> MovementObservation:
        if not fix.valid:
            return MovementObservation(moving=None, distance_since_previous_m=None)
        distance = None
        if self._previous is not None:
            distance = haversine_meters(self._previous, fix)
        self._previous = fix
        moving = fix.speed_kph >= self._minimum_speed_kph or (
            distance is not None and distance >= self._minimum_distance_m
        )
        return MovementObservation(moving=moving, distance_since_previous_m=distance)


def haversine_meters(first: GpsFix, second: GpsFix) -> float:
    """Great-circle distance between two GPS fixes in metres."""
    earth_radius_m = 6_371_000.0
    delta_latitude = radians(second.latitude - first.latitude)
    delta_longitude = radians(second.longitude - first.longitude)
    latitude_a = radians(first.latitude)
    latitude_b = radians(second.latitude)
    value = sin(delta_latitude / 2) ** 2 + cos(latitude_a) * cos(latitude_b) * sin(delta_longitude / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(value))
