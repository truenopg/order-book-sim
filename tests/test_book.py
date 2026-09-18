import unittest

from lob import LimitOrderBook, Side


class TestMatching(unittest.TestCase):
    def setUp(self):
        self.book = LimitOrderBook()

    def test_resting_orders_define_best_quotes(self):
        self.book.add_limit_order(Side.BUY, 99.0, 10)
        self.book.add_limit_order(Side.BUY, 99.5, 5)
        self.book.add_limit_order(Side.SELL, 100.5, 7)
        self.assertEqual(self.book.best_bid, 99.5)
        self.assertEqual(self.book.best_ask, 100.5)
        self.assertAlmostEqual(self.book.mid_price, 100.0)
        self.assertAlmostEqual(self.book.spread, 1.0)

    def test_crossing_limit_order_matches_then_rests(self):
        self.book.add_limit_order(Side.SELL, 100.0, 10)
        trades = self.book.add_limit_order(Side.BUY, 100.5, 6)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)  # resting order sets the price
        self.assertEqual(trades[0].qty, 6)
        # the 4 unconsumed shares of the resting ask stay on the book
        self.assertEqual(self.book.depth(Side.SELL), [(100.0, 4)])
        self.assertIsNone(self.book.best_bid)

    def test_limit_remainder_rests(self):
        self.book.add_limit_order(Side.SELL, 100.0, 4)
        self.book.add_limit_order(Side.BUY, 100.0, 10)
        self.assertEqual(self.book.depth(Side.BUY), [(100.0, 6)])

    def test_market_order_walks_levels(self):
        self.book.add_limit_order(Side.SELL, 100.0, 5)
        self.book.add_limit_order(Side.SELL, 100.1, 5)
        trades = self.book.add_market_order(Side.BUY, 8)
        self.assertEqual([(t.price, t.qty) for t in trades], [(100.0, 5), (100.1, 3)])
        self.assertEqual(self.book.best_ask, 100.1)

    def test_time_priority_within_level(self):
        self.book.add_limit_order(Side.SELL, 100.0, 5)
        self.book.add_limit_order(Side.SELL, 100.0, 5)
        trades = self.book.add_market_order(Side.BUY, 5)
        self.assertEqual(trades[0].maker_id, 1)  # first in, first out

    def test_cancel_removes_liquidity(self):
        self.book.add_limit_order(Side.BUY, 99.0, 10)
        self.assertTrue(self.book.cancel(1))
        self.assertIsNone(self.book.best_bid)
        self.assertFalse(self.book.cancel(1))  # already gone

    def test_no_trade_when_not_crossed(self):
        self.book.add_limit_order(Side.BUY, 99.0, 10)
        trades = self.book.add_limit_order(Side.SELL, 99.5, 10)
        self.assertEqual(trades, [])
        self.assertAlmostEqual(self.book.spread, 0.5)

    def test_event_log_records_everything(self):
        self.book.add_limit_order(Side.BUY, 99.0, 10)
        self.book.add_limit_order(Side.SELL, 99.0, 4)
        kinds = [e.kind for e in self.book.events]
        self.assertEqual(kinds, ["limit", "limit", "trade"])


class TestSimulation(unittest.TestCase):
    def test_simulation_runs_and_produces_history(self):
        import random
        from lob.agents import MarketMaker, NoiseTrader
        from lob.sim import Simulation

        rng = random.Random(3)
        sim = Simulation([MarketMaker(rng), NoiseTrader(rng)], seed=3)
        sim.run(300)
        self.assertEqual(len(sim.mid_history), 300)
        self.assertGreater(len(sim.book.trades), 0)

    def test_deterministic_given_seed(self):
        import random
        from lob.agents import MarketMaker, NoiseTrader
        from lob.sim import Simulation

        def run():
            rng = random.Random(11)
            sim = Simulation([MarketMaker(rng), NoiseTrader(rng)], seed=11)
            sim.run(200)
            return sim.mid_history

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
