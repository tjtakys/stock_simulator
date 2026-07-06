from __future__ import annotations

from datetime import date

import pandas as pd

from run_backtest import run_one_day
from src.simulator.order import Action


class _ExecutionPriceStrategy:
    name = "execution_price_strategy"

    def decide(self, obs: dict) -> Action:
        if obs["timestamp"] == pd.Timestamp("2026-06-24 09:00:00"):
            return Action.BUY
        return Action.CLOSE

    def execution_price(self, obs: dict, action: Action) -> float | None:
        if action == Action.BUY:
            return 95.0
        return None


def test_run_one_day_uses_strategy_execution_price(monkeypatch):
    minute = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-24 09:00:00", "2026-06-24 09:01:00"]),
            "open": [100.0, 100.0],
            "high": [101.0, 106.0],
            "low": [99.0, 99.0],
            "close": [100.0, 105.0],
            "volume": [1000, 1500],
        }
    )
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-23"]),
            "open": [90.0],
            "high": [100.0],
            "low": [85.0],
            "close": [95.0],
            "volume": [1000],
        }
    )

    monkeypatch.setattr("run_backtest.get_strategy", lambda name: _ExecutionPriceStrategy())
    monkeypatch.setattr("src.simulator.environment.load_market_data", lambda *args, **kwargs: (minute, daily))

    trades, _, metrics = run_one_day(
        "285A",
        date(2026, 6, 24),
        "execution_price_strategy",
        1,
        "sample",
        False,
    )

    assert trades.iloc[0]["entry_price"] == 95.0
    assert trades.iloc[0]["exit_price"] == 105.0
    assert metrics["total_pnl"] == 10.0
