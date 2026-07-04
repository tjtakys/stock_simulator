from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd


def write_html_report(
    path: Path,
    *,
    symbol: str,
    trading_date: str,
    strategy_name: str,
    metrics: dict,
    trades: pd.DataFrame,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_rows = "\n".join(
        f"<tr><th>{escape(str(key))}</th><td>{_format_value(value)}</td></tr>" for key, value in metrics.items()
    )
    trades_html = trades.to_html(index=False, escape=True) if not trades.empty else "<p>No trades.</p>"
    body = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{escape(symbol)} {escape(trading_date)} {escape(strategy_name)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2933; }}
    table {{ border-collapse: collapse; margin: 16px 0; width: 100%; max-width: 960px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px 10px; text-align: right; }}
    th {{ background: #f0f4f8; text-align: left; }}
    h1, h2 {{ margin-bottom: 8px; }}
  </style>
</head>
<body>
  <h1>Backtest Report</h1>
  <p>{escape(symbol)} / {escape(trading_date)} / {escape(strategy_name)}</p>
  <h2>Metrics</h2>
  <table>{metric_rows}</table>
  <h2>Trades</h2>
  {trades_html}
</body>
</html>
"""
    path.write_text(body, encoding="utf-8")
    return path


def _format_value(value: object) -> str:
    if isinstance(value, float):
        if value == float("inf"):
            return "inf"
        return f"{value:,.2f}"
    return escape(str(value))
