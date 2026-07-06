from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.simulator.order import Action
from src.simulator.position import Position, PositionSide
from src.strategies.base import get_strategy
from src.strategies.daytrade_modes import CombinedLowRiskStrategy, ElementBb3ReversalShortStrategy


def _daily_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-05-01", periods=30, freq="B"),
            "open": [105.0] * 30,
            "high": [112.0] * 30,
            "low": [100.0] * 30,
            "close": [110.0] * 30,
            "volume": [1200] * 30,
            "daily_ma_5": [106.0] * 30,
            "daily_ma_25": [100.0] * 30,
            "daily_ma_75": [95.0] * 30,
            "daily_volume_ma_20": [1000.0] * 30,
        }
    )


def _low_risk_obs(position: Position | None = None, timestamp: datetime | None = None, fills=None, trades=None) -> dict:
    count = 31
    minute = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-24 09:05:00", periods=count, freq="min"),
            "open": [110.0] * count,
            "high": [108.0] * (count - 1) + [111.0],
            "low": [104.0] * (count - 1) + [100.1],
            "close": [106.0] * (count - 1) + [110.0],
            "volume": [1000] * count,
            "vwap": [100.0] * count,
            "ma_5": [104.0] * (count - 1) + [105.0],
            "ma_25": [99.0] * (count - 6) + [100.0, 100.2, 100.4, 100.6, 100.8, 101.0],
            "ma_75": [98.0] * count,
            "bb_upper_2": [120.0] * count,
            "bb_upper_3": [130.0] * count,
            "volume_ratio_5_to_25": [1.1] * count,
            "recent_5min_volume": [5000.0] * count,
            "avg_30min_volume": [4000.0] * count,
        }
    )
    if timestamp is not None:
        minute.loc[count - 1, "timestamp"] = pd.Timestamp(timestamp)
    return {
        "timestamp": minute.iloc[-1]["timestamp"],
        "current_price": float(minute.iloc[-1]["close"]),
        "minute_bars": minute,
        "daily_bars": _daily_frame(),
        "position": position or Position(),
        "fills": fills or [],
        "trades": trades or [],
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "initial_cash": 10_000_000.0,
    }


def test_combined_low_risk_enters_on_vwap_pullback_setup():
    assert CombinedLowRiskStrategy().decide(_low_risk_obs()) == Action.BUY


def test_combined_low_risk_stops_new_entries_after_max_trades():
    fills = [{"action": "OPEN"}, {"action": "OPEN"}, {"action": "OPEN"}]

    assert CombinedLowRiskStrategy().decide(_low_risk_obs(fills=fills)) == Action.HOLD


def test_daytrade_mode_force_exits_after_1450():
    position = Position(side=PositionSide.LONG, quantity=1, entry_price=100.0, entry_time=datetime(2026, 6, 24, 9, 30))

    assert CombinedLowRiskStrategy().decide(_low_risk_obs(position=position, timestamp=datetime(2026, 6, 24, 14, 50))) == Action.CLOSE


def test_element_bb3_reversal_short_sells_only_overheated_reversal():
    obs = _low_risk_obs()
    minute = obs["minute_bars"].copy()
    minute.loc[minute.index[-2], "close"] = 121.0
    minute.loc[minute.index[-1], ["open", "high", "low", "close", "vwap", "bb_upper_3", "volume_ratio_5_to_25"]] = [
        122.0,
        123.0,
        119.0,
        120.0,
        100.0,
        115.0,
        1.1,
    ]
    obs["minute_bars"] = minute
    obs["current_price"] = 120.0

    assert ElementBb3ReversalShortStrategy().decide(obs) == Action.SELL


def test_get_strategy_returns_new_daytrade_mode():
    assert isinstance(get_strategy("combined_low_risk"), CombinedLowRiskStrategy)
