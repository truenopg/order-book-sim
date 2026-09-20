# order-book-sim

A small, dependency-free limit order book (LOB) simulator in Python, built to
explore market microstructure: how spreads, depth, and price impact emerge
from simple order-flow rules.

## What it does

- **Matching engine** with standard price-time priority: market, limit, and
  cancel orders; partial fills; FIFO within a price level; trade prices set by
  the resting order.
- **Stochastic agents** trading against the book:
  - `MarketMaker` quotes a two-sided market around the mid and skews quotes
    against its inventory.
  - `NoiseTrader` sends random market and limit orders with heavy-tailed sizes.
  - `MomentumTrader` trades in the direction of the recent mid-price move.
  - `InformedTrader` knows a random-walk fundamental value and pushes the
    price toward it when the mid drifts too far.
- **Replayable event log**: every order, cancel, and trade is recorded, so any
  run can be reconstructed exactly (`examples/replay_log.py` saves a JSONL log
  and rebuilds the book from the file, verifying a tick-for-tick match).
- **Microstructure metrics**: spread distribution, realized volatility, book
  imbalance, and a signed price-impact proxy (correlation between trade sign
  and the subsequent mid move).

## Why

Order books are where price discovery actually happens, and none of the
interesting questions ("what sets the spread?", "how much does my market order
move the price?", "what does a market maker's inventory do to its quotes?")
have closed-form answers. Simulating lets you poke at them directly.

## Run it

```bash
python examples/run_simulation.py --steps 5000 --seed 7
python examples/run_simulation.py --steps 5000 --seed 7 --plot midprice.png --events-out events.csv
python -m unittest discover -s tests   # test suite
```

No dependencies for the core; the optional plot needs matplotlib.

Sample output (seed 7, 5000 steps):

```
steps              5000
events             65633
trades             2801
final mid          99.1597
spread mean/min/max 0.0317 / 0.0019 / 0.0600
realized vol/step  0.000962
signed impact (r)  -0.133
book imbalance     -0.043
```

The clearly negative signed impact is a real property of this toy world, not
a bug: with a market maker re-quoting around the mid every step, aggressive
flow mean-reverts quickly, so trade sign anti-predicts the next move at short
lags. (Exact per-step trade timing makes the reversal show up even more
strongly than coarse event-log interpolation.)

`examples/mm_strength_experiment.py` varies the market maker's requote
probability and shows the flip directly:

```
MM requote p   trades   vol/step  impact r
        1.00     2244   0.001107    -0.003
        0.70     2147   0.000039     0.039
        0.40     2124   0.000043     0.089
        0.15     2130   0.000031     0.139
```

A market maker glued to the mid erases impact; a weaker one lets aggressive
flow move the price persistently - which is what real impact looks like.

`examples/imbalance_signal_experiment.py` asks whether top-of-book imbalance
predicts the next mid move. Without informed flow it does not (r ~ 0 at every
lag). Add an `InformedTrader` and the signal appears, matching what real
markets show:

```
lag    no informed     informed
  1        +0.004        +0.068
  3        +0.001        +0.079
  5        -0.008        +0.093
 10        +0.003        +0.093
 25        +0.001        +0.089
```

## Layout

```
lob/book.py      matching engine + book state
lob/agents.py    order-flow agents
lob/sim.py       simulation loop
lob/metrics.py   microstructure statistics
examples/        runnable demo + experiments
tests/           unittest suite
```

## Roadmap

- LOBSTER/ITCH message import for real-data replay
- Latency and queue-position modelling
- Spoofing/quote-stuffing stress tests

## License

MIT - see [LICENSE](LICENSE).
