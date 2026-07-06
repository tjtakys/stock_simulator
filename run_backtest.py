from __future__ import annotations

import argparse
from datetime import date, datetime

import pandas as pd

from src.analysis.metrics import calculate_metrics
from src.analysis.report import write_html_report
from src.config import DEFAULT_DATE, DEFAULT_ORDER_QUANTITY, DEFAULT_SYMBOL, EQUITY_DIR, REPORTS_DIR, TRADES_DIR, ensure_project_dirs
from src.risk.risk_manager import RiskManager
from src.simulator.environment import TradingEnvironment
from src.strategies.base import get_strategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daytrade strategy backtest.")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--strategy", default="vwap_ma_breakout")
    parser.add_argument("--quantity", type=int, default=DEFAULT_ORDER_QUANTITY)
    parser.add_argument("--data-source", choices=["yahoo", "sample"], default="yahoo")
    parser.add_argument("--refresh-data", action="store_true")
    return parser.parse_args()


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _dates(args: argparse.Namespace) -> list[date]:
    if args.start and args.end:
        return list(pd.bdate_range(start=args.start, end=args.end).date)
    return [_as_date(args.date)]


def run_one_day(
    symbol: str,
    trading_date: date,
    strategy_name: str,
    quantity: int,
    data_source: str,
    refresh_data: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    strategy = get_strategy(strategy_name)
    risk = RiskManager()
    env = TradingEnvironment(
        symbol=symbol,
        trading_date=trading_date,
        order_quantity=quantity,
        data_source=data_source,
        force_refresh=refresh_data,
    )
    obs = env.reset()
    equity_rows = []

    while True:
        action = strategy.decide(obs)
        approved_action, risk_reason = risk.approve(action, obs, quantity)
        execution_price = strategy.execution_price(obs, approved_action) if approved_action == action else None
        obs, reward, done, info = env.step(approved_action, quantity, execution_price=execution_price)
        equity_rows.append(
            {
                "timestamp": obs["timestamp"],
                "date": trading_date.isoformat(),
                "action": approved_action.value,
                "risk_reason": risk_reason,
                "reward": reward,
                "realized_pnl": obs["realized_pnl"],
                "unrealized_pnl": obs["unrealized_pnl"],
                "equity": obs["equity"],
            }
        )
        if done:
            break

    trades = env.broker.trades_frame()
    equity = pd.DataFrame(equity_rows)
    metrics = calculate_metrics(trades, equity)
    return trades, equity, metrics


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    all_trades = []
    all_equity = []
    for trading_date in _dates(args):
        trades, equity, _ = run_one_day(
            args.symbol,
            trading_date,
            args.strategy,
            args.quantity,
            args.data_source,
            args.refresh_data,
        )
        all_trades.append(trades)
        all_equity.append(equity)

    trades_frame = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    equity_frame = pd.concat(all_equity, ignore_index=True) if all_equity else pd.DataFrame()
    metrics = calculate_metrics(trades_frame, equity_frame)

    label = args.date if not (args.start and args.end) else f"{args.start}_{args.end}"
    stem = f"{args.symbol}_{label}_{args.strategy}"
    trades_path = TRADES_DIR / f"{stem}_trades.csv"
    equity_path = EQUITY_DIR / f"{stem}_equity.csv"
    report_path = REPORTS_DIR / f"{stem}.html"

    trades_path.parent.mkdir(parents=True, exist_ok=True)
    equity_path.parent.mkdir(parents=True, exist_ok=True)
    trades_frame.to_csv(trades_path, index=False)
    equity_frame.to_csv(equity_path, index=False)
    write_html_report(
        report_path,
        symbol=args.symbol,
        trading_date=label,
        strategy_name=args.strategy,
        metrics=metrics,
        trades=trades_frame,
    )

    print(f"trades: {trades_path}")
    print(f"equity: {equity_path}")
    print(f"report: {report_path}")
    print(f"total_pnl: {metrics['total_pnl']:.2f}")
    print(f"trade_count: {metrics['trade_count']}")


if __name__ == "__main__":
    main()
