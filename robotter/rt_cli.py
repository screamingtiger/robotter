"""Interactive command loop for the Arduino Q RT tank controller."""

from .commands import CommandProcessor
from .rt_bridge import RtTankClient


def main() -> None:
    tank = RtTankClient()
    try:
        tank.connect()
        commands = CommandProcessor(tank)
        print("robotter RT control. Commands: ARM STOP FWD n REV n LEFT n RIGHT n L90 R90")
        while line := input("> "):
            try:
                print(commands.execute(line).name.value)
            except (RuntimeError, ValueError) as error:
                print(f"error: {error}")
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        tank.close()


if __name__ == "__main__":
    main()
