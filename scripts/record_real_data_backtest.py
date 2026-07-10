from __future__ import annotations

# ruff: noqa: E402

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run_backtest import run_one_day  # noqa: E402
from src.analysis.backtest_records import build_backtest_record, record_backtest_result  # noqa: E402
from src.analysis.metrics import calculate_metrics  # noqa: E402
from src.analysis.report import write_html_report  # noqa: E402
from src.analysis.trade_chart import write_trade_chart  # noqa: E402
from src.config import (
    BACKTEST_CHARTS_DIR,
    DEFAULT_ORDER_QUANTITY,
    EQUITY_DIR,
    REPORTS_DIR,
    TRADES_DIR,
    ensure_project_dirs,
    symbol_display_name,
)  # noqa: E402
from src.data.loader import load_market_data  # noqa: E402


JST = ZoneInfo("Asia/Tokyo")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real-data backtest and record the result.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--symbol-name", default="")
    parser.add_argument("--date", default=_today_jst().isoformat())
    parser.add_argument("--strategy", default="combined_normal")
    parser.add_argument("--quantity", type=int, default=DEFAULT_ORDER_QUANTITY)
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--memo", default="")
    parser.add_argument("--include-readme", action="store_true")
    parser.add_argument("--recorded-on", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trading_date = _as_date(args.date)
    symbol = args.symbol.strip().upper()
    symbol_name = args.symbol_name.strip() or symbol_display_name(symbol)

    ensure_project_dirs()
    trades, equity, metrics = run_one_day(
        symbol=symbol,
        trading_date=trading_date,
        strategy_name=args.strategy,
        quantity=args.quantity,
        data_source="yahoo",
        refresh_data=args.refresh_data,
    )
    report_path = _write_outputs(
        symbol=symbol,
        trading_date=trading_date,
        strategy_name=args.strategy,
        trades=trades,
        equity=equity,
    )
    minute, daily = load_market_data(symbol, trading_date, generate_if_missing=False, data_source="yahoo")
    chart_path = _write_chart(
        symbol=symbol,
        trading_date=trading_date,
        strategy_name=args.strategy,
        minute=minute,
        daily=daily,
        trades=trades,
    )
    record = build_backtest_record(
        symbol=symbol,
        symbol_name=symbol_name,
        trading_date=trading_date,
        strategy_name=args.strategy,
        quantity=args.quantity,
        metrics=metrics,
        minute=minute,
        daily=daily,
        report_path=report_path,
        chart_path=chart_path,
        memo=args.memo,
        include_in_readme=args.include_readme,
        recorded_on=_as_date(args.recorded_on) if args.recorded_on else _today_jst(),
    )
    record_backtest_result(record)

    print("recorded: docs/REAL_DATA_BACKTESTS.md")
    print(f"chart: {chart_path}")
    print(f"report: {report_path}")
    print(f"total_pnl: {metrics['total_pnl']:.2f}")
    print(f"trade_count: {metrics['trade_count']}")
    print(f"win_rate: {metrics['win_rate']:.4f}")


def _write_outputs(
    *,
    symbol: str,
    trading_date: date,
    strategy_name: str,
    trades: pd.DataFrame,
    equity: pd.DataFrame,
) -> Path:
    metrics = calculate_metrics(trades, equity)
    stem = f"{symbol}_{trading_date.isoformat()}_{strategy_name}"
    trades_path = TRADES_DIR / f"{stem}_trades.csv"
    equity_path = EQUITY_DIR / f"{stem}_equity.csv"
    report_path = REPORTS_DIR / f"{stem}.html"

    trades_path.parent.mkdir(parents=True, exist_ok=True)
    equity_path.parent.mkdir(parents=True, exist_ok=True)
    trades.to_csv(trades_path, index=False)
    equity.to_csv(equity_path, index=False)
    write_html_report(
        report_path,
        symbol=symbol,
        trading_date=trading_date.isoformat(),
        strategy_name=strategy_name,
        metrics=metrics,
        trades=trades,
    )
    return report_path


def _write_chart(
    *,
    symbol: str,
    trading_date: date,
    strategy_name: str,
    minute: pd.DataFrame,
    daily: pd.DataFrame,
    trades: pd.DataFrame,
) -> Path:
    chart_path = BACKTEST_CHARTS_DIR / f"{symbol}_{trading_date.isoformat()}_{strategy_name}_chart.html"
    return write_trade_chart(
        chart_path,
        symbol=symbol,
        trading_date=trading_date.isoformat(),
        strategy_name=strategy_name,
        minute=minute,
        daily=daily,
        trades=trades,
    )


def _today_jst() -> date:
    return datetime.now(JST).date()


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


if __name__ == "__main__":
    main()
