from __future__ import annotations

import contextlib
import io
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import pandas as pd

from src.config import DEFAULT_DATE, DEFAULT_SYMBOL, RAW_DATA_DIR, ensure_project_dirs


SOURCE_NAME = "yahoo_finance"
YAHOO_MINUTE_DIR = RAW_DATA_DIR / "yahoo" / "minute"
YAHOO_DAILY_DIR = RAW_DATA_DIR / "yahoo" / "daily"


class RealDataUnavailable(RuntimeError):
    pass


def yahoo_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if "." in normalized:
        return normalized
    if re.fullmatch(r"\d{3,4}[A-Z]?", normalized):
        return f"{normalized}.T"
    return normalized


def yahoo_minute_data_path(symbol: str, trading_date: str | date) -> Path:
    return YAHOO_MINUTE_DIR / f"{symbol.upper()}_{_as_date(trading_date).isoformat()}_1min.csv"


def yahoo_daily_data_path(symbol: str) -> Path:
    return YAHOO_DAILY_DIR / f"{symbol.upper()}_daily.csv"


def ensure_yahoo_data(
    symbol: str = DEFAULT_SYMBOL,
    trading_date: str | date = DEFAULT_DATE,
    *,
    force_refresh: bool = False,
) -> tuple[Path, Path]:
    ensure_project_dirs()
    YAHOO_MINUTE_DIR.mkdir(parents=True, exist_ok=True)
    YAHOO_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    target_date = _as_date(trading_date)
    minute_path = yahoo_minute_data_path(symbol, target_date)
    daily_path = yahoo_daily_data_path(symbol)

    if force_refresh or not _is_yahoo_cache("minute", minute_path, symbol, target_date):
        minute = fetch_yahoo_minute_bars(symbol, target_date)
        minute.to_csv(minute_path, index=False)
        _write_metadata("minute", minute_path, symbol, target_date)

    if force_refresh or not _is_yahoo_cache("daily", daily_path, symbol, target_date):
        daily = fetch_yahoo_daily_bars(symbol, target_date)
        daily.to_csv(daily_path, index=False)
        _write_metadata("daily", daily_path, symbol, target_date)

    return minute_path, daily_path


def fetch_yahoo_minute_bars(symbol: str, trading_date: str | date) -> pd.DataFrame:
    yf = _import_yfinance()
    target_date = _as_date(trading_date)
    ticker = yahoo_symbol(symbol)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        frame = yf.download(
            ticker,
            start=target_date.isoformat(),
            end=(target_date + timedelta(days=1)).isoformat(),
            interval="1m",
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=False,
        )
    frame = _flatten_yfinance_frame(frame)
    if frame.empty:
        raise RealDataUnavailable(
            f"1分足データを取得できませんでした: {ticker} {target_date.isoformat()}。"
            "Yahoo Financeの1分足は取得可能期間が短く、銘柄や日付によって提供されないことがあります。"
        )

    time_column = _time_column(frame)
    timestamps = _to_tokyo_naive(frame[time_column])
    result = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": frame["Open"],
            "high": frame["High"],
            "low": frame["Low"],
            "close": frame["Close"],
            "volume": frame["Volume"].fillna(0).astype(int),
        }
    ).dropna(subset=["timestamp", "open", "high", "low", "close"])
    result = result[result["timestamp"].dt.date == target_date]
    result = result.sort_values("timestamp").reset_index(drop=True)
    if result.empty:
        raise RealDataUnavailable(f"{ticker} の {target_date.isoformat()} には1分足データがありません。")
    return _round_prices(result)


def fetch_yahoo_daily_bars(symbol: str, trading_date: str | date, lookback_days: int = 180) -> pd.DataFrame:
    yf = _import_yfinance()
    target_date = _as_date(trading_date)
    ticker = yahoo_symbol(symbol)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        frame = yf.download(
            ticker,
            start=(target_date - timedelta(days=lookback_days)).isoformat(),
            end=(target_date + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=False,
        )
    frame = _flatten_yfinance_frame(frame)
    if frame.empty:
        raise RealDataUnavailable(f"日足データを取得できませんでした: {ticker}")

    time_column = _time_column(frame)
    dates = _to_tokyo_naive(frame[time_column]).dt.date
    result = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "open": frame["Open"],
            "high": frame["High"],
            "low": frame["Low"],
            "close": frame["Close"],
            "volume": frame["Volume"].fillna(0).astype(int),
        }
    ).dropna(subset=["date", "open", "high", "low", "close"])
    result = result[result["date"].dt.date <= target_date]
    result = result.sort_values("date").reset_index(drop=True)
    if result.empty:
        raise RealDataUnavailable(f"{ticker} の {target_date.isoformat()} 以前の日足データがありません。")
    return _round_prices(result)


def _import_yfinance():
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RealDataUnavailable(
            "実データ取得には yfinance が必要です。`conda run -n sim pip install yfinance` を実行してください。"
        ) from exc
    return yf


def _flatten_yfinance_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.copy()
        frame.columns = [column[0] for column in frame.columns]
    return frame.reset_index()


def _time_column(frame: pd.DataFrame) -> str:
    for column in ["Datetime", "Date", "index"]:
        if column in frame.columns:
            return column
    raise RealDataUnavailable("Yahoo Financeの返却データに日時列が見つかりません。")


def _to_tokyo_naive(values: pd.Series) -> pd.Series:
    timestamps = pd.to_datetime(values)
    if getattr(timestamps.dt, "tz", None) is not None:
        timestamps = timestamps.dt.tz_convert("Asia/Tokyo").dt.tz_localize(None)
    return timestamps


def _round_prices(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    price_cols = ["open", "high", "low", "close"]
    result[price_cols] = result[price_cols].round(1)
    return result


def _metadata_path(kind: Literal["minute", "daily"], data_path: Path) -> Path:
    del kind
    return data_path.with_name(f"{data_path.stem}_meta.json")


def _is_yahoo_cache(kind: Literal["minute", "daily"], data_path: Path, symbol: str, trading_date: date) -> bool:
    if not data_path.exists():
        return False
    metadata_path = _metadata_path(kind, data_path)
    if not metadata_path.exists():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if metadata.get("source") != SOURCE_NAME or metadata.get("symbol") != symbol.upper():
        return False

    if kind == "minute":
        return metadata.get("trading_date") == trading_date.isoformat()

    try:
        frame = pd.read_csv(data_path, parse_dates=["date"])
    except (OSError, ValueError, pd.errors.ParserError):
        return False
    return not frame.empty and frame["date"].dt.date.max() >= trading_date


def _write_metadata(kind: Literal["minute", "daily"], data_path: Path, symbol: str, trading_date: date) -> None:
    metadata = {
        "source": SOURCE_NAME,
        "symbol": symbol.upper(),
        "yahoo_symbol": yahoo_symbol(symbol),
        "trading_date": trading_date.isoformat(),
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    _metadata_path(kind, data_path).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()
