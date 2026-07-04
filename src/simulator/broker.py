from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd

from src.simulator.order import Action, Order, OrderSide
from src.simulator.position import Position, PositionSide
from src.simulator.trade_log import Trade


class Broker(ABC):
    @abstractmethod
    def submit_order(self, order: Order, price: float, timestamp: datetime) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_position(self) -> Position:
        raise NotImplementedError

    @abstractmethod
    def get_account(self, price: float | None = None) -> dict:
        raise NotImplementedError


class SimulatedBroker(Broker):
    def __init__(self, symbol: str, initial_cash: float = 1_000_000.0) -> None:
        self.symbol = symbol
        self.initial_cash = initial_cash
        self.position = Position()
        self.realized_pnl = 0.0
        self.trades: list[Trade] = []
        self.fills: list[dict] = []

    def reset(self) -> None:
        self.position = Position()
        self.realized_pnl = 0.0
        self.trades = []
        self.fills = []

    def submit_order(self, order: Order, price: float, timestamp: datetime) -> dict:
        action = Action.BUY if order.side == OrderSide.BUY else Action.SELL
        return self.execute_action(action, price, timestamp, order.quantity)

    def execute_action(self, action: Action, price: float, timestamp: datetime, quantity: int) -> dict:
        if action == Action.HOLD:
            return {"status": "held", "trade": None}
        if quantity <= 0:
            return {"status": "rejected", "reason": "注文株数は1株以上にしてください。", "trade": None}

        if action == Action.CLOSE:
            return self._close(price, timestamp)
        if action == Action.BUY:
            if self.position.side == PositionSide.SHORT:
                return self._close(price, timestamp)
            return self._open_or_add(PositionSide.LONG, quantity, price, timestamp)
        if action == Action.SELL:
            if self.position.side == PositionSide.LONG:
                return self._close(price, timestamp)
            return self._open_or_add(PositionSide.SHORT, quantity, price, timestamp)

        return {"status": "ignored", "reason": f"未対応の操作です: {action}", "trade": None}

    def _open_or_add(self, side: PositionSide, quantity: int, price: float, timestamp: datetime) -> dict:
        required_cash = price * quantity
        available_cash = self.available_cash()
        if required_cash > available_cash:
            return {
                "status": "rejected",
                "reason": f"買付余力が不足しています。必要額 {required_cash:,.0f}円 / 余力 {available_cash:,.0f}円",
                "trade": None,
            }

        if self.position.is_flat:
            self.position = Position(side=side, quantity=quantity, entry_price=price, entry_time=timestamp)
            position_action = "OPEN"
        else:
            assert self.position.entry_price is not None
            if self.position.side != side:
                return {"status": "ignored", "reason": "反対方向の建玉があります。先に決済してください。", "trade": None}
            total_quantity = self.position.quantity + quantity
            average_price = ((self.position.entry_price * self.position.quantity) + (price * quantity)) / total_quantity
            self.position = Position(
                side=side,
                quantity=total_quantity,
                entry_price=average_price,
                entry_time=self.position.entry_time or timestamp,
            )
            position_action = "ADD"

        fill = {
            "timestamp": timestamp,
            "symbol": self.symbol,
            "action": "OPEN",
            "position_action": position_action,
            "side": side.value,
            "quantity": quantity,
            "price": price,
            "position_quantity": self.position.quantity,
            "average_entry_price": self.position.entry_price,
        }
        self.fills.append(fill)
        return {"status": "filled", "fill": fill, "trade": None}

    def _close(self, price: float, timestamp: datetime) -> dict:
        if self.position.is_flat:
            return {"status": "ignored", "reason": "決済できる建玉がありません。", "trade": None}

        assert self.position.entry_price is not None
        assert self.position.entry_time is not None

        if self.position.side == PositionSide.LONG:
            pnl = (price - self.position.entry_price) * self.position.quantity
        else:
            pnl = (self.position.entry_price - price) * self.position.quantity

        trade = Trade(
            symbol=self.symbol,
            entry_time=self.position.entry_time,
            exit_time=timestamp,
            side=self.position.side,
            quantity=self.position.quantity,
            entry_price=self.position.entry_price,
            exit_price=price,
            pnl=pnl,
        )
        self.trades.append(trade)
        self.realized_pnl += pnl
        fill = {
            "timestamp": timestamp,
            "symbol": self.symbol,
            "action": "CLOSE",
            "side": self.position.side.value,
            "quantity": self.position.quantity,
            "price": price,
            "pnl": pnl,
        }
        self.fills.append(fill)
        self.position = Position()
        return {"status": "filled", "fill": fill, "trade": trade}

    def unrealized_pnl(self, price: float | None) -> float:
        if price is None or self.position.is_flat or self.position.entry_price is None:
            return 0.0
        if self.position.side == PositionSide.LONG:
            return (price - self.position.entry_price) * self.position.quantity
        return (self.position.entry_price - price) * self.position.quantity

    def committed_notional(self) -> float:
        if self.position.is_flat or self.position.entry_price is None:
            return 0.0
        return self.position.entry_price * self.position.quantity

    def available_cash(self) -> float:
        return self.initial_cash + self.realized_pnl - self.committed_notional()

    def get_position(self) -> Position:
        return self.position

    def get_account(self, price: float | None = None) -> dict:
        unrealized = self.unrealized_pnl(price)
        return {
            "initial_cash": self.initial_cash,
            "committed_notional": self.committed_notional(),
            "available_cash": self.available_cash(),
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized,
            "equity": self.initial_cash + self.realized_pnl + unrealized,
        }

    def trades_frame(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "entry_time",
                    "exit_time",
                    "side",
                    "quantity",
                    "entry_price",
                    "exit_price",
                    "pnl",
                ]
            )
        return pd.DataFrame(
            [
                {
                    "symbol": trade.symbol,
                    "entry_time": trade.entry_time,
                    "exit_time": trade.exit_time,
                    "side": trade.side.value,
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl": trade.pnl,
                }
                for trade in self.trades
            ]
        )
