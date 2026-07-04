import pandas as pd

from src.data.loader import _pad_market_open
from src.data.providers.yahoo import yahoo_symbol


def test_yahoo_symbol_appends_tokyo_suffix_for_japanese_codes():
    assert yahoo_symbol("285A") == "285A.T"
    assert yahoo_symbol("7203") == "7203.T"


def test_yahoo_symbol_keeps_explicit_suffix_or_us_ticker():
    assert yahoo_symbol("285A.T") == "285A.T"
    assert yahoo_symbol("AAPL") == "AAPL"


def test_pad_market_open_adds_missing_opening_minutes_from_daily_open():
    minute = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-07-02 09:15:00", "2026-07-02 09:16:00"]),
            "open": [79130.0, 80890.0],
            "high": [80980.0, 80990.0],
            "low": [79000.0, 79450.0],
            "close": [80850.0, 79450.0],
            "volume": [0, 428100],
        }
    )
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-01", "2026-07-02"]),
            "open": [91180.0, 79130.0],
            "high": [93060.0, 80990.0],
            "low": [87120.0, 75000.0],
            "close": [88130.0, 76260.0],
            "volume": [29322300, 44758400],
        }
    )

    result = _pad_market_open(minute, daily, pd.Timestamp("2026-07-02").date())

    assert result.iloc[0]["timestamp"] == pd.Timestamp("2026-07-02 09:00:00")
    assert result.iloc[14]["timestamp"] == pd.Timestamp("2026-07-02 09:14:00")
    assert result.iloc[0]["close"] == 79130.0
    assert result.iloc[:15]["volume"].sum() == 0
    assert result.iloc[15]["timestamp"] == pd.Timestamp("2026-07-02 09:15:00")
