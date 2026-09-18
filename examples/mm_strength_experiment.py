#!/usr/bin/env python3
"""How does market-maker strength shape short-horizon price impact?

Runs the same agent mix while varying the market maker's requote probability:
a MM that re-quotes every step pins the mid and makes aggressive flow
mean-revert; a weaker MM lets impact persist. Prints signed impact per regime.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lob.agents import MarketMaker, MomentumTrader, NoiseTrader
from lob.metrics import realized_volatility, signed_impact
from lob.sim import Simulation


def run_regime(requote_prob: float, steps: int = 4000, seed: int = 7) -> tuple:
    rng = random.Random(seed)
    agents = [
        MarketMaker(rng, levels=3, requote_prob=requote_prob),
        NoiseTrader(rng, arrival_prob=0.40),
        MomentumTrader(rng, arrival_prob=0.20),
    ]
    sim = Simulation(agents, seed=seed)
    sim.run(steps)
    return (
        len(sim.book.trades),
        realized_volatility(sim.mid_history),
        signed_impact(sim.book, sim.mid_history, trade_steps=sim.trade_steps),
    )


def main() -> None:
    print(f"{'MM requote p':>12} {'trades':>8} {'vol/step':>10} {'impact r':>9}")
    for p in (1.0, 0.7, 0.4, 0.15):
        trades, vol, impact = run_regime(p)
        print(f"{p:>12.2f} {trades:>8} {vol:>10.6f} {impact:>9.3f}")


if __name__ == "__main__":
    main()
