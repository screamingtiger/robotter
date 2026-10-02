import unittest

from robotter.gps import GpsClient, MovementVerifier, parse_snapshot


class FakeBridge:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.connected = False
        self.calls = []

    def connect(self, timeout):
        self.connected = True

    def call(self, method, timeout):
        self.calls.append((method, timeout))
        return self.snapshot

    def disconnect(self):
        self.connected = False


class GpsTests(unittest.TestCase):
    def test_snapshot_decoding(self):
        fix = parse_snapshot("1|41.1234567|-87.1234567|3.704|91.2|9|0.8|183.4|500")
        self.assertTrue(fix.valid)
        self.assertEqual(9, fix.satellites)
        self.assertEqual(500, fix.age_ms)

    def test_client_uses_gps_snapshot_endpoint(self):
        bridge = FakeBridge("0|0|0|0|0|0|0|0|9999")
        client = GpsClient(bridge)
        client.connect()
        self.assertFalse(client.snapshot().valid)
        self.assertEqual([("gps.snapshot", 5)], bridge.calls)
        client.close()

    def test_movement_is_ground_motion_not_body_direction(self):
        verifier = MovementVerifier()
        stopped = parse_snapshot("1|41.0|-87.0|0.0|0.0|8|1.0|200|100")
        moving = parse_snapshot("1|41.0000100|-87.0|1.5|90.0|8|1.0|200|100")
        self.assertFalse(verifier.observe(stopped).moving)
        observation = verifier.observe(moving)
        self.assertTrue(observation.moving)
        self.assertIsNotNone(observation.distance_since_previous_m)


if __name__ == "__main__":
    unittest.main()
