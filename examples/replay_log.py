#!/usr/bin/env python3
"""Run a simulation, save the event log, and rebuild the book from the file.

Proof that the event log is a complete record: the replayed book matches the
original tick for tick (depth on both sides, trade count).
"""
from __future__ import annotations

import argparse
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lob.agents import InformedTrader, MarketMaker, NoiseTrader
from lob.replay import events_from_jsonl, events_to_jsonl, replay, state_fingerprint
from lob.sim import Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--log", type=str, default=None, help="keep the JSONL log here")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    sim = Simulation(
        [MarketMaker(rng, levels=3), NoiseTrader(rng), InformedTrader(rng)],
        seed=args.seed,
    )
    sim.run(args.steps)

    path = args.log or tempfile.mktemp(prefix="lob-events-", suffix=".jsonl")
    n = events_to_jsonl(sim.book.events, path)
    rebuilt = replay(events_from_jsonl(path))

    match = state_fingerprint(sim.book) == state_fingerprint(rebuilt)
    print(f"steps {args.steps}, events {n}, trades {len(sim.book.trades)}")
    print(f"log written to {path}")
    print(f"replay matches original book: {match}")
    if not match:
        sys.exit(1)


if __name__ == "__main__":
    main()
