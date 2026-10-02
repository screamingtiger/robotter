"""Processor-facing motion mnemonics and their dispatcher."""

from dataclasses import dataclass
from enum import Enum

from .tank import TankDrive


class CommandName(Enum):
    ARM = "ARM"
    STOP = "STOP"
    FORWARD = "FWD"
    REVERSE = "REV"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    LEFT_90 = "L90"
    RIGHT_90 = "R90"


@dataclass(frozen=True)
class Command:
    name: CommandName
    speed: float | None = None


_ALIASES = {"FORWARD": "FWD", "REVERSE": "REV", "ESTOP": "STOP"}
_SPEED_COMMANDS = {CommandName.FORWARD, CommandName.REVERSE, CommandName.LEFT, CommandName.RIGHT}


def parse_command(line: str) -> Command:
    parts = line.strip().upper().split()
    if not parts:
        raise ValueError("empty command")
    mnemonic = _ALIASES.get(parts[0], parts[0])
    try:
        name = CommandName(mnemonic)
    except ValueError as error:
        raise ValueError(f"unknown command: {parts[0]}") from error
    if name in _SPEED_COMMANDS:
        if len(parts) != 2:
            raise ValueError(f"{name.value} requires a speed from 0.0 through 1.0")
        try:
            speed = float(parts[1])
        except ValueError as error:
            raise ValueError("speed must be numeric") from error
        if not 0.0 <= speed <= 1.0:
            raise ValueError("speed must be between 0.0 and 1.0")
        return Command(name, speed)
    if len(parts) != 1:
        raise ValueError(f"{name.value} does not accept arguments")
    return Command(name)


class CommandProcessor:
    def __init__(self, tank: TankDrive) -> None:
        self._tank = tank

    def execute(self, line: str) -> Command:
        command = parse_command(line)
        match command.name:
            case CommandName.ARM:
                self._tank.arm()
            case CommandName.STOP:
                self._tank.stop()
            case CommandName.FORWARD:
                self._tank.forward(command.speed or 0.0)
            case CommandName.REVERSE:
                self._tank.reverse(command.speed or 0.0)
            case CommandName.LEFT:
                self._tank.pivot_left(command.speed or 0.0)
            case CommandName.RIGHT:
                self._tank.pivot_right(command.speed or 0.0)
            case CommandName.LEFT_90:
                self._tank.turn_left_90()
            case CommandName.RIGHT_90:
                self._tank.turn_right_90()
        return command
