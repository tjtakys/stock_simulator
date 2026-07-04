from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DEFAULT_DATE, DEFAULT_SYMBOL, RAW_DAILY_DIR, RAW_MINUTE_DIR, ensure_project_dirs


SAMPLE_PRICE_BASES = {
    "285A": 90_000.0,
}


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def minute_data_path(symbol: str, trading_date: str | date) -> Path:
    return RAW_MINUTE_DIR / f"{symbol}_{_as_date(trading_date).isoformat()}_1min.csv"


def daily_data_path(symbol: str) -> Path:
    return RAW_DAILY_DIR / f"{symbol}_daily.csv"


def _sample_base_price(symbol: str) -> float:
    return SAMPLE_PRICE_BASES.get(symbol.upper(), 2_500.0)


def _session_minutes(trading_date: date) -> list[datetime]:
    morning_start = datetime.combine(trading_date, time(9, 0))
    afternoon_start = datetime.combine(trading_date, time(12, 30))
    morning = [morning_start + timedelta(minutes=i) for i in range(150)]
    afternoon = [afternoon_start + timedelta(minutes=i) for i in range(180)]
    return morning + afternoon


def generate_minute_sample(symbol: str = DEFAULT_SYMBOL, trading_date: str | date = DEFAULT_DATE) -> pd.DataFrame:
    target_date = _as_date(trading_date)
    seed = int(target_date.strftime("%Y%m%d")) % (2**32)
    rng = np.random.default_rng(seed)
    timestamps = _session_minutes(target_date)

    base = _sample_base_price(symbol)
    scale = base / 2_500.0
    drift = np.linspace(-15.0, 30.0, len(timestamps)) * scale
    cycles = 18.0 * scale * np.sin(np.linspace(0, 5.5 * np.pi, len(timestamps)))
    shocks = rng.normal(0.0, 7.0 * scale, len(timestamps)).cumsum() * 0.22
    closes = base + drift + cycles + shocks
    opens = np.r_[base, closes[:-1]]
    spreads = rng.uniform(4.0 * scale, 18.0 * scale, len(timestamps))
    highs = np.maximum(opens, closes) + spreads
    lows = np.minimum(opens, closes) - spreads
    volumes = rng.integers(35_000, 180_000, len(timestamps))

    first_15 = min(15, len(volumes))
    volumes[:first_15] = (volumes[:first_15] * 1.8).astype(int)

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )
    price_cols = ["open", "high", "low", "close"]
    frame[price_cols] = frame[price_cols].round(1)
    return frame


def generate_daily_sample(symbol: str = DEFAULT_SYMBOL, end_date: str | date = DEFAULT_DATE, days: int = 100) -> pd.DataFrame:
    last_date = _as_date(end_date)
    dates = pd.bdate_range(end=last_date, periods=days).date
    rng = np.random.default_rng(285)
    returns = rng.normal(0.0015, 0.023, len(dates))
    close = (_sample_base_price(symbol) * 0.92) * np.cumprod(1.0 + returns)
    open_ = np.r_[close[0] * (1.0 - rng.normal(0, 0.01)), close[:-1]]
    intraday = rng.uniform(0.012, 0.055, len(dates))
    high = np.maximum(open_, close) * (1.0 + intraday)
    low = np.minimum(open_, close) * (1.0 - intraday)
    volume = rng.integers(7_000_000, 28_000_000, len(dates))

    frame = pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )

    target_day = frame["date"] == last_date
    if target_day.any():
        minute = generate_minute_sample(symbol=symbol, trading_date=end_date)
        frame.loc[target_day, "open"] = float(minute["open"].iloc[0])
        frame.loc[target_day, "high"] = float(minute["high"].max())
        frame.loc[target_day, "low"] = float(minute["low"].min())
        frame.loc[target_day, "close"] = float(minute["close"].iloc[-1])
        frame.loc[target_day, "volume"] = int(minute["volume"].sum())

    price_cols = ["open", "high", "low", "close"]
    frame[price_cols] = frame[price_cols].round(1)
    return frame


def ensure_sample_data(symbol: str = DEFAULT_SYMBOL, trading_date: str | date = DEFAULT_DATE) -> tuple[Path, Path]:
    ensure_project_dirs()
    minute_path = minute_data_path(symbol, trading_date)
    daily_path = daily_data_path(symbol)

    minute_has_external_metadata = _has_source_metadata(minute_path, "yahoo_finance")
    if (
        not minute_path.exists()
        or _looks_like_stale_sample(minute_path, symbol, "timestamp")
        or minute_has_external_metadata
    ):
        generate_minute_sample(symbol, trading_date).to_csv(minute_path, index=False)
        if minute_has_external_metadata:
            _remove_source_metadata(minute_path, "yahoo_finance")

    target_date = _as_date(trading_date)
    write_daily = not daily_path.exists()
    if not write_daily:
        existing = pd.read_csv(daily_path, parse_dates=["date"])
        write_daily = target_date not in set(existing["date"].dt.date)
        if _looks_like_stale_sample(daily_path, symbol, "date"):
            write_daily = True
        daily_has_external_metadata = _has_source_metadata(daily_path, "yahoo_finance")
        if daily_has_external_metadata:
            write_daily = True

    if write_daily:
        generate_daily_sample(symbol, trading_date).to_csv(daily_path, index=False)
        if "daily_has_external_metadata" in locals() and daily_has_external_metadata:
            _remove_source_metadata(daily_path, "yahoo_finance")

    return minute_path, daily_path


def _looks_like_stale_sample(path: Path, symbol: str, date_column: str) -> bool:
    if symbol.upper() != "285A" or not path.exists():
        return False
    try:
        frame = pd.read_csv(path, parse_dates=[date_column])
    except (ValueError, FileNotFoundError, pd.errors.ParserError):
        return False
    if frame.empty or "close" not in frame:
        return False
    return float(frame["close"].median()) < 10_000.0


def _has_source_metadata(path: Path, source: str) -> bool:
    candidates = [
        path.with_name(f"{path.stem}_meta.json"),
        path.with_name(f"{path.stem}.meta.json"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            metadata = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("source") == source:
            return True
    return False


def _remove_source_metadata(path: Path, source: str) -> None:
    candidates = [
        path.with_name(f"{path.stem}_meta.json"),
        path.with_name(f"{path.stem}.meta.json"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            metadata = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("source") == source:
            candidate.unlink()
