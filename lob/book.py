"""Price-time priority limit order book with an integrated matching engine."""
from __future__ import annotations

from bisect import insort
from collections import deque
from typing import Deque, Dict, List, Optional

from .orders import Event, Order, Side, Trade


class LimitOrderBook:
    """A single-instrument limit order book.

    Bids and asks are kept as price -> FIFO queue of orders, with the sorted
    price lists maintained incrementally. Matching follows standard
    price-time priority: an incoming order matches against the best opposite
    price first, oldest order first within a level, and any unmatched
    remainder of a limit order rests in the book.

    Every operation is appended to ``events`` so a simulation can be
    replayed exactly from its log.
    """

    def __init__(self, tick_size: float = 0.01) -> None:
        self.tick_size = tick_size
        self.bids: Dict[float, Deque[Order]] = {}
        self.asks: Dict[float, Deque[Order]] = {}
        self.bid_prices: List[float] = []  # ascending
        self.ask_prices: List[float] = []  # ascending
        self._live: Dict[int, Order] = {}  # order_id -> resting order
        self.events: List[Event] = []
        self.trades: List[Trade] = []
        self._seq = 0

    # ------------------------------------------------------------------ API

    def add_limit_order(self, side: Side, price: float, qty: int) -> List[Trade]:
        order = self._next_order(side, qty, price)
        self._log("limit", order)
        trades = self._match(order)
        if order.qty > 0:
            self._rest(order)
        return trades

    def add_market_order(self, side: Side, qty: int) -> List[Trade]:
        order = self._next_order(side, qty, None)
        self._log("market", order)
        return self._match(order)

    def cancel(self, order_id: int) -> bool:
        order = self._live.pop(order_id, None)
        if order is None:
            return False
        levels, prices = self._side_map(order.side)
        queue = levels[order.price]
        queue.remove(order)
        if not queue:
            del levels[order.price]
            prices.remove(order.price)
        self._seq += 1
        self.events.append(Event(self._seq, "cancel", {"order_id": order_id}))
        return True

    # -------------------------------------------------------------- quoting

    @property
    def best_bid(self) -> Optional[float]:
        return self.bid_prices[-1] if self.bid_prices else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.ask_prices[0] if self.ask_prices else None

    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    def depth(self, side: Side, levels: int = 5) -> List[tuple]:
        """Top ``levels`` (price, total_qty) on one side, best first."""
        if side is Side.BUY:
            prices = self.bid_prices[::-1][:levels]
            return [(p, sum(o.qty for o in self.bids[p])) for p in prices]
        prices = self.ask_prices[:levels]
        return [(p, sum(o.qty for o in self.asks[p])) for p in prices]

    def imbalance(self, levels: int = 5) -> Optional[float]:
        """(bid_qty - ask_qty) / (bid_qty + ask_qty) over the top levels."""
        bid_qty = sum(q for _, q in self.depth(Side.BUY, levels))
        ask_qty = sum(q for _, q in self.depth(Side.SELL, levels))
        total = bid_qty + ask_qty
        return (bid_qty - ask_qty) / total if total else None

    # ------------------------------------------------------------ internals

    def _next_order(self, side: Side, qty: int, price: Optional[float]) -> Order:
        self._seq += 1
        order = Order(order_id=self._seq, side=side, qty=qty, price=price, seq=self._seq)
        return order

    def _log(self, kind: str, order: Order) -> None:
        self.events.append(
            Event(
                order.seq,
                kind,
                {"order_id": order.order_id, "side": order.side.value,
                 "price": order.price, "qty": order.qty},
            )
        )

    def _side_map(self, side: Side):
        if side is Side.BUY:
            return self.bids, self.bid_prices
        return self.asks, self.ask_prices

    def _rest(self, order: Order) -> None:
        levels, prices = self._side_map(order.side)
        if order.price not in levels:
            levels[order.price] = deque()
            insort(prices, order.price)
        levels[order.price].append(order)
        self._live[order.order_id] = order

    def _match(self, incoming: Order) -> List[Trade]:
        trades: List[Trade] = []
        opp_levels, opp_prices = self._side_map(incoming.side.opposite)
        while incoming.qty > 0 and opp_prices:
            best = opp_prices[0] if incoming.side is Side.BUY else opp_prices[-1]
            if not incoming.is_market:
                crossed = best <= incoming.price if incoming.side is Side.BUY else best >= incoming.price
                if not crossed:
                    break
            queue = opp_levels[best]
            while incoming.qty > 0 and queue:
                resting = queue[0]
                fill = min(incoming.qty, resting.qty)
                incoming.qty -= fill
                resting.qty -= fill
                trade = Trade(
                    price=best,
                    qty=fill,
                    maker_id=resting.order_id,
                    taker_id=incoming.order_id,
                    taker_side=incoming.side,
                    seq=self._seq,
                )
                trades.append(trade)
                self.trades.append(trade)
                self.events.append(
                    Event(self._seq, "trade",
                          {"price": best, "qty": fill, "maker": resting.order_id,
                           "taker": incoming.order_id, "taker_side": incoming.side.value})
                )
                if resting.qty == 0:
                    queue.popleft()
                    self._live.pop(resting.order_id, None)
            if not queue:
                del opp_levels[best]
                opp_prices.remove(best)
        return trades
