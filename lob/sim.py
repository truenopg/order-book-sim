"""Simulation loop: agents act step by step against one shared book."""
from __future__ import annotations

import random
from typing import List, Optional

from .agents import Agent
from .book import LimitOrderBook
from .orders import Side


class Simulation:
    """Drives a LimitOrderBook with a population of agents.

    The book starts seeded with symmetric liquidity around
    ``reference_price`` so the spread is defined from step one.
    """

    def __init__(self, agents: List[Agent], seed: int = 0,
                 reference_price: float = 100.0, tick_size: float = 0.01) -> None:
        self.rng = random.Random(seed)
        self.book = LimitOrderBook(tick_size=tick_size)
        self.reference_price = reference_price
        self.agents = agents
        self.mid_history: List[float] = []
        self.trade_steps: List[int] = []  # step index for each trade, in trade order
        self._step = 0
        self._seed_book()

    @property
    def mid(self) -> Optional[float]:
        return self.book.mid_price

    def _seed_book(self, levels: int = 8, qty: int = 30) -> None:
        for lvl in range(1, levels + 1):
            offset = lvl * self.book.tick_size
            self.book.add_limit_order(Side.BUY, round(self.reference_price - offset, 4), qty)
            self.book.add_limit_order(Side.SELL, round(self.reference_price + offset, 4), qty)

    def step(self) -> None:
        before = len(self.book.trades)
        for agent in self.agents:
            agent.act(self)
        self.trade_steps.extend([self._step] * (len(self.book.trades) - before))
        mid = self.mid
        if mid is not None:
            self.mid_history.append(mid)
        self._step += 1

    def run(self, steps: int) -> None:
        for _ in range(steps):
            self.step()
