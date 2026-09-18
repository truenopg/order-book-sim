"""Core order and trade types for the limit order book simulator."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Side(Enum):
    BUY = "buy"
    SELL = "sell"

    @property
    def opposite(self) -> "Side":
        return Side.SELL if self is Side.BUY else Side.BUY


@dataclass
class Order:
    """A single order. price=None means a market order."""

    order_id: int
    side: Side
    qty: int
    price: Optional[float] = None  # None -> market order
    seq: int = 0  # arrival sequence number; gives time priority within a level

    @property
    def is_market(self) -> bool:
        return self.price is None


@dataclass
class Trade:
    """An executed match between a resting and an incoming order."""

    price: float
    qty: int
    maker_id: int  # resting order
    taker_id: int  # incoming order
    taker_side: Side
    seq: int


@dataclass
class Event:
    """One entry in the replayable event log."""

    seq: int
    kind: str  # "limit", "market", "cancel", "trade"
    detail: dict = field(default_factory=dict)
