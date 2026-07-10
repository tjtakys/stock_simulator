from __future__ import annotations

import pandas as pd

from src.analysis.trade_chart import fills_from_trades, write_trade_chart


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


def test_write_trade_chart_creates_png(tmp_path):
    minute = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-07-10 09:00:00",
                    "2026-07-10 09:01:00",
                    "2026-07-10 09:02:00",
                    "2026-07-10 09:03:00",
                    "2026-07-10 09:04:00",
                ]
            ),
            "open": [100.0, 101.0, 102.0, 101.0, 103.0],
            "high": [102.0, 103.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 100.0, 100.0, 102.0],
            "close": [101.0, 102.0, 101.0, 103.0, 104.0],
            "volume": [1000, 1200, 800, 1500, 1100],
        }
    )
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-09"]),
            "open": [95.0],
            "high": [105.0],
            "low": [94.0],
            "close": [100.0],
            "volume": [10000],
        }
    )
    trades = pd.DataFrame(
        {
            "symbol": ["6976"],
            "entry_time": pd.to_datetime(["2026-07-10 09:01:00"]),
            "exit_time": pd.to_datetime(["2026-07-10 09:03:00"]),
            "side": ["LONG"],
            "quantity": [100],
            "entry_price": [102.0],
            "exit_price": [103.0],
            "pnl": [100.0],
        }
    )
    chart_path = tmp_path / "chart.png"

    result = write_trade_chart(
        chart_path,
        symbol="6976",
        trading_date="2026-07-10",
        strategy_name="test_strategy",
        minute=minute,
        daily=daily,
        trades=trades,
    )

    assert result == chart_path
    assert chart_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
