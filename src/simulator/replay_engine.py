from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.registry import add_daily_indicators, add_minute_indicators


class ReplayEngine:
    def __init__(self, minute_bars: pd.DataFrame, daily_bars: pd.DataFrame, trading_date: date) -> None:
        if minute_bars.empty:
            raise ValueError("1分足データが空です。銘柄・日付・データ取得元を確認してください。")
        self.minute_bars = add_minute_indicators(minute_bars.sort_values("timestamp").reset_index(drop=True))
        self.base_daily_bars = daily_bars.sort_values("date").reset_index(drop=True)
        self.trading_date = trading_date
        self.index = 0

    def reset(self) -> dict:
        self.index = 0
        return self.current_state()

    @property
    def done(self) -> bool:
        return self.index >= len(self.minute_bars) - 1

    def advance(self) -> dict:
        if not self.done:
            self.index += 1
        return self.current_state()

    def current_bar(self) -> pd.Series:
        return self.minute_bars.iloc[self.index]

    def bars_until_now(self) -> pd.DataFrame:
        return self.minute_bars.iloc[: self.index + 1].copy()

    def current_day_bar(self) -> pd.DataFrame:
        bars = self.bars_until_now()
        first = bars.iloc[0]
        last = bars.iloc[-1]
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp(self.trading_date),
                    "open": float(first["open"]),
                    "high": float(bars["high"].max()),
                    "low": float(bars["low"].min()),
                    "close": float(last["close"]),
                    "volume": int(bars["volume"].sum()),
                }
            ]
        )

    def daily_until_now(self) -> pd.DataFrame:
        daily = self.base_daily_bars.copy()
        daily_dates = pd.to_datetime(daily["date"]).dt.date
        past_daily = daily[daily_dates < self.trading_date].copy()
        return add_daily_indicators(past_daily.reset_index(drop=True))

    def current_state(self) -> dict:
        bar = self.current_bar()
        return {
            "timestamp": bar["timestamp"],
            "current_price": float(bar["close"]),
            "minute_bars": self.bars_until_now(),
            "daily_bars": self.daily_until_now(),
            "current_bar": bar,
            "is_last_bar": self.done,
        }
