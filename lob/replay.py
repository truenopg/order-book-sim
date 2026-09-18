"""Rebuild a book by replaying its event log.

Proves the log is complete: a book replayed from its events must match the
original book's state (quotes, depth, live orders) exactly.
"""
from __future__ import annotations

import json
from typing import Iterable, List

from .book import LimitOrderBook
from .orders import Event, Side


def replay(events: Iterable[Event], tick_size: float = 0.01) -> LimitOrderBook:
    """Apply order/cancel events in sequence and return the resulting book.

    Trade events are skipped: they are outputs of matching, not inputs, and
    replaying the order flow reproduces them.
    """
    book = LimitOrderBook(tick_size=tick_size)
    for ev in events:
        if ev.kind == "limit":
            book.add_limit_order(Side(ev.detail["side"]), ev.detail["price"], ev.detail["qty"])
        elif ev.kind == "market":
            book.add_market_order(Side(ev.detail["side"]), ev.detail["qty"])
        elif ev.kind == "cancel":
            book.cancel(ev.detail["order_id"])
    return book


def events_from_jsonl(path: str) -> List[Event]:
    """Load an event log written one JSON object per line."""
    events: List[Event] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            events.append(Event(seq=row["seq"], kind=row["kind"], detail=row["detail"]))
    return events


def state_fingerprint(book: LimitOrderBook) -> tuple:
    """Comparable snapshot of book state: both sides' full depth."""
    bids = [(p, sum(o.qty for o in book.bids[p])) for p in book.bid_prices[::-1]]
    asks = [(p, sum(o.qty for o in book.asks[p])) for p in book.ask_prices]
    return (tuple(bids), tuple(asks))
