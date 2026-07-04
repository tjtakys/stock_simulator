from __future__ import annotations

import pandas as pd

from src.simulator.order import Action
from src.simulator.position import PositionSide
from src.strategies.base import Strategy


class BollingerNextBarReversionStrategy(Strategy):
    name = "bollinger_next_reversion"

    def __init__(self, stop_loss_rate: float = 0.05, min_bars: int = 20) -> None:
        self.stop_loss_rate = stop_loss_rate
        self.min_bars = min_bars

    def decide(self, obs: dict) -> Action:
        position = obs["position"]
        price = float(obs["current_price"])

        if position.side != PositionSide.FLAT:
            return self._exit_action(position.side, float(position.entry_price or price), price)

        minute = obs["minute_bars"]
        if len(minute) < self.min_bars + 1:
            return Action.HOLD

        previous = minute.iloc[-2]
        previous_close = _safe_float(previous.get("close"))
        previous_upper_3 = _safe_float(previous.get("bb_upper_3"))
        previous_lower_3 = _safe_float(previous.get("bb_lower_3"))
        if None in [previous_close, previous_upper_3, previous_lower_3]:
            return Action.HOLD

        if previous_close < previous_lower_3:
            return Action.BUY
        if previous_close > previous_upper_3:
            return Action.SELL
        return Action.HOLD

    def _exit_action(self, side: PositionSide, entry_price: float, price: float) -> Action:
        if entry_price <= 0:
            return Action.HOLD

        pnl_rate = (price - entry_price) / entry_price
        if side == PositionSide.SHORT:
            pnl_rate = -pnl_rate

        if pnl_rate > 0:
            return Action.CLOSE
        if pnl_rate <= -self.stop_loss_rate:
            return Action.CLOSE
        return Action.HOLD


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
