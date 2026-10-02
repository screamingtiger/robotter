"""Interactive command loop for the Arduino Q RT tank and camera turret."""

from .commands import CommandProcessor
from .rt_bridge import RtTankClient
from .turret import TurretClient


def main() -> None:
    tank = RtTankClient()
    turret = TurretClient()
    try:
        tank.connect()
        turret.connect()
        commands = CommandProcessor(tank, turret)
        print("robotter RT control. Commands: ARM STOP FWD n REV n LEFT n RIGHT n L90 R90 TURRET deg TCENTER")
        while line := input("> "):
            try:
                print(commands.execute(line).name.value)
            except (RuntimeError, ValueError) as error:
                print(f"error: {error}")
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        turret.close()
        tank.close()


if __name__ == "__main__":
    main()
