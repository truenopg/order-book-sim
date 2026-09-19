#!/usr/bin/env python3
"""Does order-book imbalance predict the next mid-price move?

Samples top-of-book imbalance every step of a simulation and correlates it
with the mid-price change over the next few steps. Real markets show a
clearly positive short-horizon relationship; this checks whether the toy
world reproduces it.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lob.agents import InformedTrader, MarketMaker, MomentumTrader, NoiseTrader
from lob.metrics import signal_correlation
from lob.sim import Simulation


def run(with_informed: bool, seed: int = 7) -> list:
    rng = random.Random(seed)
    agents = [
        MarketMaker(rng, levels=3),
        NoiseTrader(rng, arrival_prob=0.40),
        MomentumTrader(rng, arrival_prob=0.20),
    ]
    if with_informed:
        agents.append(InformedTrader(rng, threshold_ticks=2.0))
    sim = Simulation(agents, seed=seed)

    imbalances = []
    for _ in range(4000):
        sim.step()
        imb = sim.book.imbalance()
        imbalances.append(imb if imb is not None else 0.0)
    return [
        signal_correlation(imbalances, sim.mid_history, lag=lag)
        for lag in (1, 3, 5, 10, 25)
    ]


def main() -> None:
    lags = (1, 3, 5, 10, 25)
    without = run(with_informed=False)
    with_i = run(with_informed=True)
    print("imbalance vs forward mid move (Pearson r)")
    print(f"{'lag':>5} {'no informed':>12} {'informed':>12}")
    for lag, a, b in zip(lags, without, with_i):
        print(f"{lag:>5} {a:>+12.3f} {b:>+12.3f}")


if __name__ == "__main__":
    main()
