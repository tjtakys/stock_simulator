from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.indicators.registry import add_daily_indicators, add_minute_indicators
from src.ui.chart import minute_chart


def write_trade_chart(
    path: Path,
    *,
    symbol: str,
    trading_date: str,
    strategy_name: str,
    minute: pd.DataFrame,
    daily: pd.DataFrame,
    trades: pd.DataFrame,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    obs = {
        "minute_bars": add_minute_indicators(minute.sort_values("timestamp").reset_index(drop=True)),
        "daily_bars": add_daily_indicators(daily.sort_values("date").reset_index(drop=True)),
        "fills": fills_from_trades(trades),
    }
    fig = minute_chart(
        obs,
        show={"vwap": True, "minute_ma": True, "bollinger": True},
        display_window="全表示",
        chart_type="1分足",
    )
    fig.update_layout(
        title=f"{symbol} {trading_date} {strategy_name}",
        height=760,
    )
    fig.write_html(path, include_plotlyjs="cdn", full_html=True)
    return path


def fills_from_trades(trades: pd.DataFrame) -> list[dict]:
    if trades.empty:
        return []

    fills: list[dict] = []
    for trade in trades.itertuples(index=False):
        side = str(trade.side)
        fills.append(
            {
                "timestamp": pd.Timestamp(trade.entry_time),
                "action": "OPEN",
                "side": side,
                "quantity": int(trade.quantity),
                "price": float(trade.entry_price),
            }
        )
        fills.append(
            {
                "timestamp": pd.Timestamp(trade.exit_time),
                "action": "CLOSE",
                "side": side,
                "quantity": int(trade.quantity),
                "price": float(trade.exit_price),
                "pnl": float(trade.pnl),
            }
        )
    return fills
