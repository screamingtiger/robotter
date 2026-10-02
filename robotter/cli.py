"""Simulation-only stdin command loop for the tank control package."""

from .commands import CommandProcessor
from .pwm import MemoryPwm
from .tank import TankDrive


def main() -> None:
    pwm = MemoryPwm()
    tank = TankDrive(pwm)
    commands = CommandProcessor(tank)
    print("robotter simulator. Commands: ARM STOP FWD n REV n LEFT n RIGHT n L90 R90")
    try:
        while line := input("> "):
            try:
                command = commands.execute(line)
                print(f"{command.name.value}: {dict(pwm.pulses)}")
            except (RuntimeError, ValueError) as error:
                print(f"error: {error}")
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        tank.stop()
        print(f"STOP: {dict(pwm.pulses)}")


if __name__ == "__main__":
    main()
