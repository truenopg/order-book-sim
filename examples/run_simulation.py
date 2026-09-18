#!/usr/bin/env python3
"""Run a stochastic limit-order-book simulation and print microstructure stats.

Usage:
    python examples/run_simulation.py --steps 5000 --seed 7
    python examples/run_simulation.py --plot midprice.png --events-out events.csv
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lob.agents import MarketMaker, MomentumTrader, NoiseTrader
from lob.metrics import realized_volatility, sampled_spreads, signed_impact
from lob.sim import Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--reference-price", type=float, default=100.0)
    parser.add_argument("--plot", type=str, default=None, help="save a mid-price plot here")
    parser.add_argument("--events-out", type=str, default=None, help="write the event log as CSV")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    agents = [
        MarketMaker(rng, half_spread_ticks=2.0, levels=3),
        NoiseTrader(rng, arrival_prob=0.40),
        MomentumTrader(rng, arrival_prob=0.20),
    ]
    sim = Simulation(agents, seed=args.seed, reference_price=args.reference_price)

    spreads = []
    for _ in range(args.steps):
        sim.step()
        if sim.book.spread is not None:
            spreads.append(sim.book.spread)

    book = sim.book
    print(f"steps              {args.steps}")
    print(f"events             {len(book.events)}")
    print(f"trades             {len(book.trades)}")
    print(f"final mid          {book.mid_price:.4f}" if book.mid_price else "final mid          n/a")
    ss = sampled_spreads(spreads)
    print(f"spread mean/min/max {ss['mean']:.4f} / {ss['min']:.4f} / {ss['max']:.4f}")
    print(f"realized vol/step  {realized_volatility(sim.mid_history):.6f}")
    print(f"signed impact (r)  {signed_impact(book, sim.mid_history):.3f}")
    imb = book.imbalance()
    print(f"book imbalance     {imb:.3f}" if imb is not None else "book imbalance     n/a")

    if args.events_out:
        with open(args.events_out, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["seq", "kind", "detail"])
            for ev in book.events:
                writer.writerow([ev.seq, ev.kind, ev.detail])
        print(f"event log written to {args.events_out}")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        ax1.plot(sim.mid_history, lw=0.6)
        ax1.set_ylabel("mid price")
        ax2.plot(spreads, lw=0.6, color="darkred")
        ax2.set_ylabel("spread")
        ax2.set_xlabel("step")
        fig.tight_layout()
        fig.savefig(args.plot, dpi=120)
        print(f"plot written to {args.plot}")


if __name__ == "__main__":
    main()
