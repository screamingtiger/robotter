import unittest

from robotter.commands import CommandName, CommandProcessor, parse_command
from robotter.config import TankConfig
from robotter.pwm import MemoryPwm
from robotter.tank import TankDrive


class RobotterTests(unittest.TestCase):
    def setUp(self):
        self.waits = []
        self.pwm = MemoryPwm()
        self.tank = TankDrive(self.pwm, TankConfig(turn_90_seconds=0.25), self.waits.append)

    def test_motion_requires_explicit_arm(self):
        with self.assertRaisesRegex(RuntimeError, "not armed"):
            self.tank.forward(0.5)

    def test_forward_uses_both_tracks_and_stop_neutralizes_them(self):
        self.tank.arm()
        self.tank.forward(0.5)
        self.assertEqual({0: 1750, 1: 1750}, self.pwm.pulses)
        self.tank.stop()
        self.assertEqual({0: 1500, 1: 1500}, self.pwm.pulses)

    def test_timed_turn_stops_even_after_completion(self):
        self.tank.arm()
        self.tank.turn_left_90()
        self.assertIn(0.25, self.waits)
        self.assertEqual({0: 1500, 1: 1500}, self.pwm.pulses)

    def test_processor_mnemonics(self):
        self.assertEqual(CommandName.FORWARD, parse_command("forward 0.4").name)
        self.assertEqual(CommandName.STOP, parse_command("estop").name)
        processor = CommandProcessor(self.tank)
        processor.execute("ARM")
        processor.execute("RIGHT 0.5")
        self.assertEqual({0: 1750, 1: 1250}, self.pwm.pulses)


if __name__ == "__main__":
    unittest.main()
