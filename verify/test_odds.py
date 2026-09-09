"""Replay every published vector through the Python engine. Zero dependencies: python -m unittest."""
import json
import math
import pathlib
import unittest

from verify.odds import P_MAX, P_MIN, phi, quote, realized_sigma, target_for

VECTORS = json.loads((pathlib.Path(__file__).resolve().parent / "vectors.json").read_text(encoding="utf-8"))


class TestPhi(unittest.TestCase):
    def test_known_points(self):
        self.assertAlmostEqual(phi(0.0), 0.5, places=6)
        self.assertAlmostEqual(phi(1.0), 0.8413, places=3)
        self.assertAlmostEqual(phi(-1.0), 0.1587, places=3)
        self.assertAlmostEqual(phi(1.96), 0.9750, places=3)

    def test_symmetry(self):
        for x in (0.13, 0.84, 1.5, 2.7):
            self.assertAlmostEqual(phi(x) + phi(-x), 1.0, places=6)

    def test_matches_erf(self):
        for x in (-2.5, -0.7, 0.0, 0.42, 1.8):
            exact = 0.5 * (1 + math.erf(x / math.sqrt(2)))
            self.assertLess(abs(phi(x) - exact), 8e-8)


class TestVectors(unittest.TestCase):
    def test_every_vector(self):
        for v in VECTORS["vectors"]:
            with self.subTest(v["name"]):
                q = quote(v["cap"], v["level"], v["sigma"], v["hours"], v["kind"])
                self.assertEqual(q.yes_cents, v["yes_cents"])
                self.assertEqual(q.no_cents, v["no_cents"])
                self.assertAlmostEqual(q.d, v["d"], places=5)

    def test_sigma_series(self):
        s = VECTORS["sigma_series"]
        self.assertAlmostEqual(realized_sigma(s["closes"]), s["expected_sigma"], places=6)


class TestInvariants(unittest.TestCase):
    def test_cents_always_sum_to_a_dollar(self):
        for cap, level, sigma, hours, kind in [
            (1e5, 2e5, 0.5, 1, "touch"), (5e6, 4e6, 0.2, 12, "floor"),
            (9e8, 1e9, 1.2, 0.1, "touch"), (3e4, 2.9e4, 2.5, 24, "floor"),
        ]:
            q = quote(cap, level, sigma, hours, kind)
            self.assertEqual(q.yes_cents + q.no_cents, 100)

    def test_probability_is_clamped(self):
        far = quote(1e3, 1e12, 0.1, 0.02, "touch")
        near = quote(1e12, 1.0, 0.1, 24, "floor")
        self.assertGreaterEqual(far.p_yes, P_MIN)
        self.assertLessEqual(near.p_yes, P_MAX)

    def test_closer_target_is_never_cheaper(self):
        base = quote(100_000, 150_000, 0.6, 3, "touch")
        closer = quote(100_000, 120_000, 0.6, 3, "touch")
        self.assertGreaterEqual(closer.p_yes, base.p_yes)

    def test_more_time_helps_a_touch_market(self):
        short = quote(100_000, 150_000, 0.6, 1, "touch")
        long_ = quote(100_000, 150_000, 0.6, 8, "touch")
        self.assertGreater(long_.p_yes, short.p_yes)

    def test_more_time_hurts_a_floor_market(self):
        short = quote(100_000, 80_000, 0.6, 1, "floor")
        long_ = quote(100_000, 80_000, 0.6, 8, "floor")
        self.assertLess(long_.p_yes, short.p_yes)

    def test_volatility_scaled_target_is_above_cap(self):
        t = target_for(250_000, 0.4, 1.0, k=1.0)
        self.assertGreater(t, 250_000)

    def test_rejects_nonsense(self):
        for bad in [(0, 1, 0.5, 1), (1, 0, 0.5, 1), (1, 1, 0, 1)]:
            with self.assertRaises(ValueError):
                quote(*bad)


if __name__ == "__main__":
    unittest.main()
