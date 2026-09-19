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

from lob.agents import MarketMaker, MomentumTrader, NoiseTrader
from lob.metrics import signal_correlation
from lob.sim import Simulation


def main() -> None:
    rng = random.Random(7)
    agents = [
        MarketMaker(rng, levels=3),
        NoiseTrader(rng, arrival_prob=0.40),
        MomentumTrader(rng, arrival_prob=0.20),
    ]
    sim = Simulation(agents, seed=7)

    imbalances = []
    for _ in range(4000):
        sim.step()
        imb = sim.book.imbalance()
        imbalances.append(imb if imb is not None else 0.0)

    print("imbalance vs forward mid move (Pearson r)")
    for lag in (1, 3, 5, 10, 25):
        r = signal_correlation(imbalances, sim.mid_history, lag=lag)
        print(f"  lag {lag:>3} steps: r = {r:+.3f}")


if __name__ == "__main__":
    main()
