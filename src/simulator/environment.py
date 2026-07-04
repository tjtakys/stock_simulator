from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from src.config import DEFAULT_INITIAL_CASH, DEFAULT_ORDER_QUANTITY
from src.data.loader import DataSource, load_market_data
from src.simulator.broker import SimulatedBroker
from src.simulator.order import Action
from src.simulator.replay_engine import ReplayEngine


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


class TradingEnvironment:
    def __init__(
        self,
        symbol: str,
        trading_date: str | date,
        minute_bars: pd.DataFrame | None = None,
        daily_bars: pd.DataFrame | None = None,
        *,
        initial_cash: float = DEFAULT_INITIAL_CASH,
        order_quantity: int = DEFAULT_ORDER_QUANTITY,
        force_close_on_end: bool = True,
        data_source: DataSource = "sample",
        force_refresh: bool = False,
    ) -> None:
        self.symbol = symbol
        self.trading_date = _as_date(trading_date)
        if minute_bars is None or daily_bars is None:
            minute_bars, daily_bars = load_market_data(
                symbol,
                self.trading_date,
                data_source=data_source,
                force_refresh=force_refresh,
            )
        self.engine = ReplayEngine(minute_bars, daily_bars, self.trading_date)
        self.broker = SimulatedBroker(symbol, initial_cash=initial_cash)
        self.order_quantity = order_quantity
        self.force_close_on_end = force_close_on_end
        self.done = False
        self.last_info: dict = {}

    def reset(self) -> dict:
        self.engine.reset()
        self.broker.reset()
        self.done = False
        self.last_info = {}
        return self._observation()

    def step(self, action: Action | str, quantity: int | None = None) -> tuple[dict, float, bool, dict]:
        action = Action(action)
        quantity = quantity or self.order_quantity
        before = self.broker.get_account(self.engine.current_state()["current_price"])["equity"]

        state = self.engine.current_state()
        fill_info = self.broker.execute_action(
            action,
            price=state["current_price"],
            timestamp=state["timestamp"],
            quantity=quantity,
        )

        if self.engine.done:
            if self.force_close_on_end and not self.broker.position.is_flat:
                fill_info = self.broker.execute_action(
                    Action.CLOSE,
                    price=state["current_price"],
                    timestamp=state["timestamp"],
                    quantity=quantity,
                )
            self.done = True
        else:
            self.engine.advance()

        after = self.broker.get_account(self.engine.current_state()["current_price"])["equity"]
        reward = after - before
        obs = self._observation()
        info = {
            "fill": fill_info,
            "trades": self.broker.trades,
            "account": self.broker.get_account(obs["current_price"]),
        }
        self.last_info = info
        return obs, reward, self.done, info

    def _observation(self) -> dict:
        state = self.engine.current_state()
        minute = state["minute_bars"]
        daily = state["daily_bars"]
        latest = minute.iloc[-1]
        latest_daily = daily.iloc[-1] if not daily.empty else pd.Series(dtype="float64")
        account = self.broker.get_account(state["current_price"])
        return {
            "symbol": self.symbol,
            "date": self.trading_date,
            "timestamp": state["timestamp"],
            "current_price": state["current_price"],
            "minute_bars": minute,
            "daily_bars": daily,
            "indicators": {
                "vwap": _safe_float(latest.get("vwap")),
                "ma_5": _safe_float(latest.get("ma_5")),
                "ma_25": _safe_float(latest.get("ma_25")),
                "daily_ma_5": _safe_float(latest_daily.get("daily_ma_5")),
                "daily_ma_25": _safe_float(latest_daily.get("daily_ma_25")),
                "daily_ma_75": _safe_float(latest_daily.get("daily_ma_75")),
                "bb_middle": _safe_float(latest.get("bb_middle")),
                "bb_upper_1": _safe_float(latest.get("bb_upper_1")),
                "bb_lower_1": _safe_float(latest.get("bb_lower_1")),
                "bb_upper_2": _safe_float(latest.get("bb_upper_2")),
                "bb_lower_2": _safe_float(latest.get("bb_lower_2")),
                "bb_upper_3": _safe_float(latest.get("bb_upper_3")),
                "bb_lower_3": _safe_float(latest.get("bb_lower_3")),
            },
            "position": self.broker.get_position(),
            "fills": self.broker.fills,
            "trades": self.broker.trades,
            "realized_pnl": account["realized_pnl"],
            "unrealized_pnl": account["unrealized_pnl"],
            "equity": account["equity"],
            "initial_cash": account["initial_cash"],
            "available_cash": account["available_cash"],
            "committed_notional": account["committed_notional"],
            "done": self.done,
        }


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
