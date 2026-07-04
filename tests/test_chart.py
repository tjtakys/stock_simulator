from __future__ import annotations

import pandas as pd

from src.ui.chart import (
    _intraday_price_axis_range,
    _visible_minute_bars,
    _with_compressed_x,
    daily_chart,
    important_price_line_chart,
    intraday_chart_frame,
    long_term_chart_frame,
    minute_chart,
    neckline_selection_chart,
)


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


def test_visible_minute_bars_keeps_fixed_window_width():
    minute = pd.DataFrame(
        {
            "chart_x": [0.0, 15.0, 45.0],
            "timestamp": pd.date_range("2026-06-24 09:00:00", periods=3, freq="15min"),
            "open": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
            "close": [100, 102, 103],
            "volume": [1000, 1000, 1000],
        }
    )

    _, initial_range = _visible_minute_bars(minute.iloc[:1], "過去30分", 1)
    _, middle_range = _visible_minute_bars(minute.iloc[:2], "過去30分", 1)
    _, later_range = _visible_minute_bars(minute, "過去30分", 1)

    assert initial_range == [-30.0, 3.6]
    assert middle_range == [-15.0, 18.6]
    assert later_range == [15.0, 48.6]
    assert initial_range[1] - initial_range[0] == 33.6
    assert middle_range[1] - middle_range[0] == 33.6
    assert later_range[1] - later_range[0] == 33.6
    assert later_range[1] > minute["chart_x"].iloc[-1]


def test_with_compressed_x_connects_lunch_break():
    minute = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-24 11:29:00", "2026-06-24 12:30:00"]),
            "open": [100, 101],
            "high": [101, 102],
            "low": [99, 100],
            "close": [100, 102],
            "volume": [1000, 1000],
        }
    )

    result = _with_compressed_x(minute, 1)

    assert result["chart_x"].tolist() == [0.0, 1.0]


def test_intraday_price_axis_ignores_far_reference_prices():
    minute = pd.DataFrame(
        {
            "high": [101.0, 102.0, 101.5],
            "low": [99.0, 100.0, 100.5],
            "close": [100.0, 101.0, 101.0],
            "vwap": [100.0, 100.5, 101.0],
            "bb_upper_3": [150.0, 150.0, 150.0],
            "bb_lower_3": [50.0, 50.0, 50.0],
        }
    )

    price_range = _intraday_price_axis_range(
        minute,
        {"vwap": True, "minute_ma": False, "bollinger": True},
        [10_000.0],
    )

    assert price_range is not None
    assert price_range[0] > 95.0
    assert price_range[1] < 106.0


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


def test_neckline_selection_chart_adds_clickable_price_layer():
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

    fig = neckline_selection_chart({"daily_bars": daily}, {"daily_ma": True, "bollinger": False}, [])

    assert any(trace.name == "価格帯別出来高" for trace in fig.data)
    selector = fig.data[-1]
    assert selector.name == "価格選択"
    assert selector.customdata[0][0] is not None
    assert fig.layout.clickmode == "event+select"
    assert fig.layout.yaxis.showspikes


def test_important_price_line_chart_uses_selected_daily_range():
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2026-06-01", periods=20, freq="B"),
            "open": range(100, 120),
            "high": range(101, 121),
            "low": range(99, 119),
            "close": range(100, 120),
            "volume": [1000] * 20,
            "daily_ma_5": range(100, 120),
            "daily_ma_25": range(100, 120),
            "daily_ma_75": range(100, 120),
        }
    )
    start = daily["date"].dt.date.iloc[-5]
    end = daily["date"].dt.date.iloc[-1]

    fig = important_price_line_chart(
        {"daily_bars": daily},
        {"daily_ma": False, "bollinger": False},
        [],
        (start, end),
    )

    assert len(fig.data[0].x) == 5
    assert any(trace.name == "価格帯別出来高" for trace in fig.data)


def test_important_price_line_chart_uses_trading_day_axis_for_integer_range():
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2026-06-01", periods=20, freq="B"),
            "open": range(100, 120),
            "high": range(101, 121),
            "low": range(99, 119),
            "close": range(100, 120),
            "volume": [1000] * 20,
            "daily_ma_5": range(100, 120),
            "daily_ma_25": range(100, 120),
            "daily_ma_75": range(100, 120),
        }
    )

    fig = important_price_line_chart(
        {"daily_bars": daily},
        {"daily_ma": False, "bollinger": False},
        [],
        (10, 14),
    )

    assert list(fig.data[0].x) == [10, 11, 12, 13, 14]
    assert list(fig.layout.xaxis.range) == [9.5, 14.5]


def test_minute_chart_shows_previous_day_context_at_market_open():
    minute = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-24 09:00:00"]),
            "open": [100.0],
            "high": [100.0],
            "low": [100.0],
            "close": [100.0],
            "volume": [0],
        }
    )
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-23"]),
            "open": [105.0],
            "high": [110.0],
            "low": [95.0],
            "close": [100.0],
            "volume": [1000],
        }
    )

    fig = minute_chart(
        {"minute_bars": minute, "daily_bars": daily, "fills": []},
        {"vwap": False, "minute_ma": False, "bollinger": False},
        "過去30分",
    )

    assert any(trace.name == "前日足" for trace in fig.data)
    assert fig.layout.yaxis.range[0] < 95.0
    assert fig.layout.yaxis.range[1] > 110.0


def test_bollinger_upper_and_lower_pairs_use_same_color():
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

    fig = daily_chart({"daily_bars": daily}, {"daily_ma": False, "bollinger": True}, "日足")
    colors = {trace.name: trace.line.color for trace in fig.data if "ボリンジャー" in trace.name}

    assert colors["日足 ボリンジャー +1σ"] == colors["日足 ボリンジャー -1σ"]
    assert colors["日足 ボリンジャー +2σ"] == colors["日足 ボリンジャー -2σ"]
    assert colors["日足 ボリンジャー +3σ"] == colors["日足 ボリンジャー -3σ"]
