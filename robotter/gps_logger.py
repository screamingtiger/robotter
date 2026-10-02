"""Log RT GPS snapshots to CSV at a fixed interval."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep

from .gps import GpsClient, MovementVerifier


FIELDNAMES = [
    "logged_at_utc",
    "fix_valid",
    "latitude",
    "longitude",
    "speed_kph",
    "course_degrees",
    "satellites",
    "hdop",
    "altitude_m",
    "fix_age_ms",
    "moving",
    "distance_since_previous_m",
]


def log_forever(path: Path, interval_s: float = 0.5) -> None:
    if interval_s <= 0:
        raise ValueError("interval_s must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    client = GpsClient()
    verifier = MovementVerifier()
    client.connect()
    try:
        with path.open("a", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDNAMES)
            if output.tell() == 0:
                writer.writeheader()
            next_sample = monotonic()
            while True:
                fix = client.snapshot()
                movement = verifier.observe(fix)
                writer.writerow(
                    {
                        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                        "fix_valid": fix.valid,
                        "latitude": fix.latitude if fix.valid else "",
                        "longitude": fix.longitude if fix.valid else "",
                        "speed_kph": fix.speed_kph if fix.valid else "",
                        "course_degrees": fix.course_degrees if fix.valid else "",
                        "satellites": fix.satellites if fix.valid else "",
                        "hdop": fix.hdop if fix.valid else "",
                        "altitude_m": fix.altitude_m if fix.valid else "",
                        "fix_age_ms": fix.age_ms,
                        "moving": movement.moving if movement.moving is not None else "",
                        "distance_since_previous_m": movement.distance_since_previous_m or "",
                    }
                )
                output.flush()
                next_sample += interval_s
                sleep(max(0.0, next_sample - monotonic()))
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Log Arduino Q RT GPS fixes to CSV")
    parser.add_argument("--csv", type=Path, default=Path("logs/gps.csv"), help="output CSV path")
    parser.add_argument("--interval", type=float, default=0.5, help="sampling interval in seconds")
    arguments = parser.parse_args()
    try:
        log_forever(arguments.csv, arguments.interval)
    except KeyboardInterrupt:
        print("GPS logging stopped")


if __name__ == "__main__":
    main()
