"""Microstructure statistics computed from a finished simulation."""
from __future__ import annotations

import math
from typing import Dict, List

from .book import LimitOrderBook


def mid_returns(mid_history: List[float]) -> List[float]:
    """Simple mid-price returns; skips steps where the mid did not move."""
    return [
        (b - a) / a
        for a, b in zip(mid_history, mid_history[1:])
        if a and b != a
    ]


def realized_volatility(mid_history: List[float], annualize: bool = False,
                        steps_per_year: int = 252 * 390) -> float:
    """Std-dev of mid-price returns, optionally annualized."""
    rets = mid_returns(mid_history)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    vol = math.sqrt(var)
    return vol * math.sqrt(steps_per_year) if annualize else vol


def spread_stats(book: LimitOrderBook) -> Dict[str, float]:
    """Spread summary over the full event history is not kept; this samples
    the current book. Use ``sampled_spreads`` during a run for time stats."""
    spread = book.spread
    return {"current_spread": spread if spread is not None else float("nan")}


def sampled_spreads(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"mean": float("nan"), "min": float("nan"), "max": float("nan")}
    return {
        "mean": sum(samples) / len(samples),
        "min": min(samples),
        "max": max(samples),
    }


def signed_impact(book: LimitOrderBook, mid_history: List[float], lag: int = 5) -> float:
    """Rough price-impact proxy: correlation between trade sign and the
    mid-price move over the next ``lag`` recorded mids.

    Trade sign is +1 for a buyer-initiated trade. Returns Pearson r in
    [-1, 1]; a clearly positive value is what real impact looks like.
    """
    if not book.trades or len(mid_history) < lag + 2:
        return 0.0
    # Pair each trade (in order) with the mid move lag steps later, using the
    # trade's position in the event sequence as an approximate time index.
    n = len(mid_history)
    xs: List[float] = []
    ys: List[float] = []
    step_of_trade = _trade_step_indices(book, n)
    for trade, idx in zip(book.trades, step_of_trade):
        j = idx + lag
        if j >= n:
            break
        sign = 1.0 if trade.taker_side.value == "buy" else -1.0
        xs.append(sign)
        ys.append(mid_history[j] - mid_history[idx])
    if len(xs) < 3:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def _trade_step_indices(book: LimitOrderBook, n: int) -> List[int]:
    """Map each trade to an approximate mid-history index by interpolation
    over the event sequence."""
    if not book.events:
        return []
    last_seq = book.events[-1].seq or 1
    return [min(n - 1, int(t.seq / last_seq * (n - 1))) for t in book.trades]
