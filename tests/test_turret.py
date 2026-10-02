import unittest

from robotter.commands import CommandProcessor, parse_command
from robotter.turret import TurretClient


class FakeBridge:
    def __init__(self):
        self.calls = []
        self.connected = False

    def connect(self, timeout):
        self.connected = True

    def call(self, method, *arguments, timeout):
        self.calls.append((method, arguments, timeout))
        return True

    def disconnect(self):
        self.connected = False


class TurretTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.turret = TurretClient(self.bridge)
        self.turret.connect()

    def tearDown(self):
        self.turret.close()

    def test_center_targets_forward_calibration(self):
        self.turret.center()
        self.assertEqual(("turret.center", (), 5), self.bridge.calls[-1])

    def test_angle_is_relative_to_center_and_bounded(self):
        self.turret.set_angle_degrees(-35.0)
        self.assertEqual(("turret.set_angle", (-35.0,), 5), self.bridge.calls[-1])
        with self.assertRaises(ValueError):
            self.turret.set_angle_degrees(61.0)

    def test_processor_exposes_turret_mnemonics(self):
        class Tank:
            pass

        processor = CommandProcessor(Tank(), self.turret)
        processor.execute("TURRET -25")
        self.assertEqual(("turret.set_angle", (-25.0,), 5), self.bridge.calls[-1])
        self.assertEqual("TCENTER", parse_command("center").name.value)


if __name__ == "__main__":
    unittest.main()
