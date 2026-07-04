from __future__ import annotations

import math

import pandas as pd


def calculate_metrics(trades: pd.DataFrame, equity: pd.DataFrame | None = None) -> dict:
    pnl = trades["pnl"] if not trades.empty and "pnl" in trades else pd.Series(dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = float(abs(losses.sum())) if not losses.empty else 0.0

    metrics = {
        "total_pnl": float(pnl.sum()) if not pnl.empty else 0.0,
        "trade_count": int(len(pnl)),
        "win_rate": float((pnl > 0).mean()) if len(pnl) else 0.0,
        "average_profit": float(wins.mean()) if not wins.empty else 0.0,
        "average_loss": float(losses.mean()) if not losses.empty else 0.0,
        "max_profit": float(pnl.max()) if not pnl.empty else 0.0,
        "max_loss": float(pnl.min()) if not pnl.empty else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else math.inf if gross_profit else 0.0,
        "expectancy": float(pnl.mean()) if not pnl.empty else 0.0,
        "max_drawdown": 0.0,
        "sharpe_like": 0.0,
        "average_daily_pnl": float(pnl.sum()) if not pnl.empty else 0.0,
    }

    if equity is not None and not equity.empty and "equity" in equity:
        curve = equity["equity"].astype(float)
        drawdown = curve - curve.cummax()
        returns = curve.diff().fillna(0.0)
        metrics["max_drawdown"] = float(drawdown.min())
        std = float(returns.std(ddof=0))
        metrics["sharpe_like"] = float(returns.mean() / std) if std else 0.0

        if "date" in equity:
            daily = equity.groupby("date")["realized_pnl"].last().diff().fillna(equity.groupby("date")["realized_pnl"].last())
            metrics["average_daily_pnl"] = float(daily.mean()) if not daily.empty else metrics["total_pnl"]

    return metrics
