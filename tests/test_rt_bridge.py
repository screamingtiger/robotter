import unittest

from robotter.rt_bridge import RtTankClient


class FakeBridge:
    def __init__(self):
        self.connected = False
        self.calls = []

    def connect(self, timeout):
        self.connected = True

    def call(self, method, *args, timeout):
        self.calls.append((method, args, timeout))
        return True

    def disconnect(self):
        self.connected = False


class RtTankClientTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.tank = RtTankClient(self.bridge, heartbeat_period_s=None)
        self.tank.connect()

    def tearDown(self):
        self.tank.close()

    def test_motion_is_refused_until_connected_and_armed_by_mcu(self):
        self.tank.arm()
        self.tank.forward(0.5)
        self.assertEqual(
            [("tank.arm", (), 5), ("tank.set_tracks", (0.5, 0.5), 5)],
            self.bridge.calls,
        )

    def test_timed_turn_is_owned_by_the_rt_controller(self):
        self.tank.turn_left_90()
        self.assertEqual(
            ("tank.pivot_timed", (-1.0, 1.0, 750), 5), self.bridge.calls[-1]
        )

    def test_stop_is_sent_when_client_closes(self):
        self.tank.close()
        self.assertIn(("tank.stop", (), 5), self.bridge.calls)


if __name__ == "__main__":
    unittest.main()
