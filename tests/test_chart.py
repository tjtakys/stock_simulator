from __future__ import annotations

import pandas as pd

from src.ui.chart import intraday_chart_frame, long_term_chart_frame


def test_intraday_chart_frame_resamples_to_five_minutes():
    minute = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-24 09:00:00", periods=6, freq="min"),
            "open": [100, 101, 102, 103, 104, 105],
            "high": [101, 102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103, 104],
            "close": [101, 102, 103, 104, 105, 106],
            "volume": [100, 200, 300, 400, 500, 600],
            "vwap": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5],
        }
    )

    result = intraday_chart_frame(minute, "5分足")

    assert len(result) == 2
    assert result.iloc[0]["open"] == 100
    assert result.iloc[0]["high"] == 105
    assert result.iloc[0]["low"] == 99
    assert result.iloc[0]["close"] == 105
    assert result.iloc[0]["volume"] == 1500
    assert result.iloc[0]["vwap"] == 104.5
    assert result.iloc[1]["open"] == 105
    assert "bb_upper_1" in result.columns


def test_long_term_chart_frame_adds_bollinger_to_daily():
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2026-06-01", periods=25, freq="B"),
            "open": range(100, 125),
            "high": range(101, 126),
            "low": range(99, 124),
            "close": range(100, 125),
            "volume": [1000] * 25,
            "daily_ma_5": range(100, 125),
            "daily_ma_25": range(100, 125),
            "daily_ma_75": range(100, 125),
        }
    )

    result = long_term_chart_frame(daily, "日足")

    assert {"ma_5", "ma_25", "ma_75", "bb_upper_1", "bb_lower_3"} <= set(result.columns)
