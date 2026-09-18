"""Stochastic order-flow agents that trade against the book."""
from __future__ import annotations

import random
from typing import Optional, TYPE_CHECKING

from .orders import Side

if TYPE_CHECKING:
    from .sim import Simulation


class Agent:
    """Base class. ``act`` is called once per simulation step."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def act(self, sim: "Simulation") -> None:  # pragma: no cover - interface
        raise NotImplementedError


class NoiseTrader(Agent):
    """Sends random market orders, plus occasional limit orders near the touch.

    Arrivals are Bernoulli per step; sizes are drawn from a lognormal-ish
    distribution so most orders are small and a few are large.
    """

    def __init__(self, rng: random.Random, arrival_prob: float = 0.35,
                 limit_fraction: float = 0.5, max_qty: int = 40) -> None:
        super().__init__(rng)
        self.arrival_prob = arrival_prob
        self.limit_fraction = limit_fraction
        self.max_qty = max_qty

    def _qty(self) -> int:
        return max(1, min(self.max_qty, int(self.rng.lognormvariate(1.2, 0.9))))

    def act(self, sim: "Simulation") -> None:
        if self.rng.random() > self.arrival_prob:
            return
        side = Side.BUY if self.rng.random() < 0.5 else Side.SELL
        if self.rng.random() < self.limit_fraction and sim.mid is not None:
            offset = self.rng.uniform(0.5, 3.0) * sim.book.tick_size
            price = sim.mid - offset if side is Side.BUY else sim.mid + offset
            sim.book.add_limit_order(side, round(price, 4), self._qty())
        else:
            sim.book.add_market_order(side, self._qty())


class MarketMaker(Agent):
    """Quotes a two-sided market around the mid price.

    Keeps ``levels`` quotes per side, re-quoting each step: it cancels its
    resting orders and reposts around the current mid. Inventory risk is
    crudely managed by skewing quotes against accumulated inventory.
    """

    def __init__(self, rng: random.Random, half_spread_ticks: float = 2.0,
                 levels: int = 2, quote_qty: int = 15,
                 requote_prob: float = 1.0) -> None:
        super().__init__(rng)
        self.half_spread_ticks = half_spread_ticks
        self.levels = levels
        self.quote_qty = quote_qty
        self.requote_prob = requote_prob  # < 1 weakens the MM's grip on the mid
        self.inventory = 0
        self._resting: list[int] = []

    def act(self, sim: "Simulation") -> None:
        if self.rng.random() > self.requote_prob:
            return
        book = sim.book
        old_quotes = set(self._resting)
        for oid in old_quotes:
            book.cancel(oid)
        self._resting.clear()
        # inventory changes only when someone hits/lifts one of my quotes
        for t in book.trades:
            if t.maker_id in old_quotes:
                old_quotes.discard(t.maker_id)  # count a fill once
                self.inventory += t.qty if t.taker_side is Side.SELL else -t.qty
        mid = sim.mid
        if mid is None:
            mid = sim.reference_price
        tick = book.tick_size
        skew = self.inventory * 0.05 * tick  # quote away from inventory
        live_before = set(book._live)
        for lvl in range(1, self.levels + 1):
            offset = (self.half_spread_ticks + lvl - 1) * tick
            bid = round(mid - offset - skew, 4)
            ask = round(mid + offset - skew, 4)
            qty = max(1, int(self.quote_qty * self.rng.uniform(0.6, 1.4)))
            book.add_limit_order(Side.BUY, bid, qty)
            book.add_limit_order(Side.SELL, ask, qty)
        self._resting = sorted(set(book._live) - live_before)


class MomentumTrader(Agent):
    """Trades in the direction of the recent mid-price move."""

    def __init__(self, rng: random.Random, arrival_prob: float = 0.25,
                 lookback: int = 12, max_qty: int = 25) -> None:
        super().__init__(rng)
        self.arrival_prob = arrival_prob
        self.lookback = lookback
        self.max_qty = max_qty

    def act(self, sim: "Simulation") -> None:
        if self.rng.random() > self.arrival_prob or len(sim.mid_history) < self.lookback:
            return
        move = sim.mid_history[-1] - sim.mid_history[-self.lookback]
        if move == 0:
            return
        side = Side.BUY if move > 0 else Side.SELL
        qty = max(1, min(self.max_qty, int(abs(move) * 500)))
        sim.book.add_market_order(side, qty)
