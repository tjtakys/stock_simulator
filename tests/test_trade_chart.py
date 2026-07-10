from __future__ import annotations

import pandas as pd

from src.analysis.trade_chart import fills_from_trades


def test_fills_from_trades_builds_entry_and_exit_markers():
    trades = pd.DataFrame(
        {
            "symbol": ["6976"],
            "entry_time": pd.to_datetime(["2026-07-10 09:30:00"]),
            "exit_time": pd.to_datetime(["2026-07-10 10:00:00"]),
            "side": ["LONG"],
            "quantity": [100],
            "entry_price": [1000.0],
            "exit_price": [1010.0],
            "pnl": [1000.0],
        }
    )

    fills = fills_from_trades(trades)

    assert fills == [
        {
            "timestamp": pd.Timestamp("2026-07-10 09:30:00"),
            "action": "OPEN",
            "side": "LONG",
            "quantity": 100,
            "price": 1000.0,
        },
        {
            "timestamp": pd.Timestamp("2026-07-10 10:00:00"),
            "action": "CLOSE",
            "side": "LONG",
            "quantity": 100,
            "price": 1010.0,
            "pnl": 1000.0,
        },
    ]


def test_fills_from_trades_returns_empty_list_without_trades():
    assert fills_from_trades(pd.DataFrame()) == []
