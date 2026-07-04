from __future__ import annotations

from datetime import date, datetime
from typing import Literal

import pandas as pd

from src.config import DEFAULT_DATE, DEFAULT_SYMBOL
from src.data.providers.yahoo import ensure_yahoo_data, yahoo_daily_data_path, yahoo_minute_data_path
from src.data.sample_data import daily_data_path, ensure_sample_data, minute_data_path
from src.data.schema import DAILY_COLUMNS, MINUTE_COLUMNS, DailyBar, MinuteBar


DataSource = Literal["sample", "yahoo"]


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _require_columns(frame: pd.DataFrame, required: list[str], source: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{source} に必要な列がありません: {', '.join(missing)}")


def _validate_records(frame: pd.DataFrame, model: type[MinuteBar] | type[DailyBar]) -> None:
    for record in frame.to_dict("records"):
        model(**record)


def load_minute_bars(
    symbol: str = DEFAULT_SYMBOL,
    trading_date: str | date = DEFAULT_DATE,
    *,
    generate_if_missing: bool = True,
    data_source: DataSource = "sample",
    force_refresh: bool = False,
) -> pd.DataFrame:
    if generate_if_missing:
        if data_source == "sample":
            ensure_sample_data(symbol, trading_date)
        elif data_source == "yahoo":
            ensure_yahoo_data(symbol, trading_date, force_refresh=force_refresh)
        else:
            raise ValueError(f"未対応のデータ種別です: {data_source}")

    path = yahoo_minute_data_path(symbol, trading_date) if data_source == "yahoo" else minute_data_path(symbol, trading_date)
    if not path.exists():
        raise FileNotFoundError(f"1分足データが見つかりません: {path}")

    frame = pd.read_csv(path, parse_dates=["timestamp"])
    _require_columns(frame, MINUTE_COLUMNS, str(path))
    frame = frame[MINUTE_COLUMNS].sort_values("timestamp").reset_index(drop=True)
    _validate_records(frame, MinuteBar)
    return frame


def load_daily_bars(
    symbol: str = DEFAULT_SYMBOL,
    trading_date: str | date = DEFAULT_DATE,
    *,
    generate_if_missing: bool = True,
    data_source: DataSource = "sample",
    force_refresh: bool = False,
) -> pd.DataFrame:
    if generate_if_missing:
        if data_source == "sample":
            ensure_sample_data(symbol, trading_date)
        elif data_source == "yahoo":
            ensure_yahoo_data(symbol, trading_date, force_refresh=force_refresh)
        else:
            raise ValueError(f"未対応のデータ種別です: {data_source}")

    path = yahoo_daily_data_path(symbol) if data_source == "yahoo" else daily_data_path(symbol)
    if not path.exists():
        raise FileNotFoundError(f"日足データが見つかりません: {path}")

    target_date = _as_date(trading_date)
    frame = pd.read_csv(path, parse_dates=["date"])
    _require_columns(frame, DAILY_COLUMNS, str(path))
    frame = frame[DAILY_COLUMNS].sort_values("date").reset_index(drop=True)
    frame = frame[frame["date"].dt.date <= target_date].reset_index(drop=True)
    _validate_records(frame, DailyBar)
    return frame


def load_market_data(
    symbol: str = DEFAULT_SYMBOL,
    trading_date: str | date = DEFAULT_DATE,
    *,
    generate_if_missing: bool = True,
    data_source: DataSource = "sample",
    force_refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if generate_if_missing:
        if data_source == "sample":
            ensure_sample_data(symbol, trading_date)
        elif data_source == "yahoo":
            ensure_yahoo_data(symbol, trading_date, force_refresh=force_refresh)
        else:
            raise ValueError(f"未対応のデータ種別です: {data_source}")

    minute = load_minute_bars(
        symbol,
        trading_date,
        generate_if_missing=False,
        data_source=data_source,
        force_refresh=force_refresh,
    )
    daily = load_daily_bars(
        symbol,
        trading_date,
        generate_if_missing=False,
        data_source=data_source,
        force_refresh=force_refresh,
    )
    return minute, daily
