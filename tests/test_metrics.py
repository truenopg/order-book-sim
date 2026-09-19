import math
import unittest

from lob.metrics import mid_returns, realized_volatility, sampled_spreads


class TestMidReturns(unittest.TestCase):
    def test_basic(self):
        rets = mid_returns([100.0, 101.0, 101.0, 99.0])
        self.assertEqual(len(rets), 2)  # unchanged step skipped
        self.assertAlmostEqual(rets[0], 0.01)

    def test_empty(self):
        self.assertEqual(mid_returns([]), [])
        self.assertEqual(mid_returns([100.0]), [])


class TestVolatility(unittest.TestCase):
    def test_constant_series_has_zero_vol(self):
        self.assertEqual(realized_volatility([100.0] * 100), 0.0)

    def test_too_short(self):
        self.assertEqual(realized_volatility([100.0, 100.0]), 0.0)

    def test_positive_for_moving_series(self):
        series = [100.0 + (i % 5) * 0.1 for i in range(50)]
        self.assertGreater(realized_volatility(series), 0.0)


class TestSampledSpreads(unittest.TestCase):
    def test_stats(self):
        ss = sampled_spreads([0.01, 0.02, 0.03])
        self.assertAlmostEqual(ss["mean"], 0.02)
        self.assertEqual(ss["min"], 0.01)
        self.assertEqual(ss["max"], 0.03)

    def test_empty_is_nan(self):
        ss = sampled_spreads([])
        self.assertTrue(math.isnan(ss["mean"]))


if __name__ == "__main__":
    unittest.main()


class TestSignalCorrelation(unittest.TestCase):
    def test_perfect_signal(self):
        from lob.metrics import signal_correlation
        # signal at t equals the mid move t -> t+1 exactly
        mid = [100.0, 101.0, 99.0, 102.0]
        signals = [1.0, -2.0, 3.0, 0.0]
        self.assertAlmostEqual(signal_correlation(signals, mid, lag=1), 1.0)

    def test_constant_inputs(self):
        from lob.metrics import signal_correlation
        self.assertEqual(signal_correlation([0.0] * 10, [100.0] * 10), 0.0)
