from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.indicators.bollinger import bollinger_bands
from src.indicators.moving_average import moving_average


INTRADAY_INTERVALS = {
    "1分足": 1,
    "3分足": 3,
    "5分足": 5,
    "10分足": 10,
    "30分足": 30,
    "60分足": 60,
}

BOLLINGER_STYLES = [
    ("bb_upper_1", "+1σ", "#2563eb"),
    ("bb_lower_1", "-1σ", "#2563eb"),
    ("bb_upper_2", "+2σ", "#dc2626"),
    ("bb_lower_2", "-2σ", "#dc2626"),
    ("bb_upper_3", "+3σ", "#64748b"),
    ("bb_lower_3", "-3σ", "#64748b"),
]

IMPORTANT_PRICE_COLUMN_WIDTHS = [0.84, 0.16]
IMPORTANT_PRICE_HORIZONTAL_SPACING = 0.02
UP_CANDLE_COLOR = "#16a34a"
DOWN_CANDLE_COLOR = "#dc2626"
FLAT_CANDLE_COLOR = "#64748b"


def minute_chart(
    obs: dict,
    show: dict[str, bool],
    display_window: str = "過去30分",
    necklines: list[dict] | None = None,
    chart_type: str = "1分足",
) -> go.Figure:
    interval_minutes = intraday_interval_minutes(chart_type)
    minute = intraday_chart_frame(obs["minute_bars"], chart_type)
    daily = obs["daily_bars"]
    necklines = necklines or []
    chart_minute = _with_compressed_x(minute, interval_minutes)
    visible_minute, x_range = _visible_minute_bars(chart_minute, display_window, interval_minutes)
    previous = _latest_known_daily(daily)
    previous_context_x = _previous_day_context_x(visible_minute, x_range, interval_minutes, previous)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.72, 0.28],
    )
    if previous is not None and previous_context_x is not None:
        fig.add_trace(
            go.Candlestick(
                x=[previous_context_x],
                open=[float(previous["open"])],
                high=[float(previous["high"])],
                low=[float(previous["low"])],
                close=[float(previous["close"])],
                customdata=[[pd.Timestamp(previous["date"]).strftime("%Y-%m-%d"), float(previous["volume"])]],
                hovertemplate=(
                    "前日 %{customdata[0]}<br>"
                    "始値 %{open:,.1f}円<br>"
                    "高値 %{high:,.1f}円<br>"
                    "安値 %{low:,.1f}円<br>"
                    "終値 %{close:,.1f}円<br>"
                    "出来高 %{customdata[1]:,.0f}<extra></extra>"
                ),
                name="前日足",
                opacity=0.45,
                increasing=dict(line=dict(color="#64748b"), fillcolor="rgba(100, 116, 139, 0.32)"),
                decreasing=dict(line=dict(color="#64748b"), fillcolor="rgba(100, 116, 139, 0.32)"),
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Candlestick(
            x=visible_minute["chart_x"],
            open=visible_minute["open"],
            high=visible_minute["high"],
            low=visible_minute["low"],
            close=visible_minute["close"],
            customdata=visible_minute["timestamp"].dt.strftime("%H:%M"),
            hovertemplate=(
                "%{customdata}<br>"
                "始値 %{open:,.1f}円<br>"
                "高値 %{high:,.1f}円<br>"
                "安値 %{low:,.1f}円<br>"
                "終値 %{close:,.1f}円<extra></extra>"
            ),
            name=chart_type,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=visible_minute["chart_x"],
            y=visible_minute["volume"],
            name="出来高",
            marker=dict(color=_volume_bar_colors(visible_minute)),
            customdata=visible_minute["timestamp"].dt.strftime("%H:%M"),
            hovertemplate="%{customdata}<br>出来高 %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    if show.get("vwap") and "vwap" in visible_minute:
        fig.add_trace(
            go.Scatter(
                x=visible_minute["chart_x"],
                y=visible_minute["vwap"],
                name="出来高加重平均価格",
                line=dict(width=1.6),
            ),
            row=1,
            col=1,
        )
    if show.get("minute_ma"):
        fig.add_trace(
            go.Scatter(
                x=visible_minute["chart_x"],
                y=visible_minute["ma_5"],
                name="移動平均5",
                line=dict(width=1.2),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=visible_minute["chart_x"],
                y=visible_minute["ma_25"],
                name="移動平均25",
                line=dict(width=1.2),
            ),
            row=1,
            col=1,
        )
    if show.get("bollinger"):
        for column, label, color in BOLLINGER_STYLES:
            fig.add_trace(
                go.Scatter(
                    x=visible_minute["chart_x"],
                    y=visible_minute[column],
                    name=f"ボリンジャー {label}",
                    line=dict(width=1.0, dash="dot", color=color),
                ),
                row=1,
                col=1,
            )

    _add_trade_markers(fig, visible_minute, obs.get("fills", []))

    if previous is not None:
        for column, label in [("high", "前日高値"), ("low", "前日安値"), ("close", "前日終値")]:
            fig.add_hline(y=float(previous[column]), line_width=1, line_dash="dash", annotation_text=label, row=1, col=1)
    _add_necklines(fig, necklines, row=1, col=1)

    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    if x_range is not None:
        fig.update_xaxes(range=x_range, row=1, col=1)
        fig.update_xaxes(range=x_range, row=2, col=1)
    tick_values, tick_text = _time_ticks(visible_minute)
    if tick_values:
        fig.update_xaxes(tickmode="array", tickvals=tick_values, ticktext=tick_text, row=1, col=1)
        fig.update_xaxes(tickmode="array", tickvals=tick_values, ticktext=tick_text, row=2, col=1)
    y_range = _intraday_price_axis_range(visible_minute, show, [line["price"] for line in necklines])
    if y_range is not None and previous is not None and previous_context_x is not None:
        y_range = _expand_price_axis_range(y_range, [float(previous["low"]), float(previous["high"])])
    if y_range is not None:
        fig.update_yaxes(range=y_range, row=1, col=1)
    fig.update_yaxes(title_text="価格", tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(title_text="出来高", tickformat=",d", row=2, col=1)
    return fig


def daily_chart(
    obs: dict,
    show: dict[str, bool],
    chart_type: str = "日足",
    necklines: list[dict] | None = None,
) -> go.Figure:
    necklines = necklines or []
    daily = long_term_chart_frame(obs["daily_bars"], chart_type)
    fig = go.Figure()
    _add_long_term_price_traces(fig, daily, show, chart_type)
    _add_necklines(fig, necklines)
    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    y_range = _price_axis_range(
        daily,
        {"daily_ma": show.get("daily_ma", False), "bollinger": show.get("bollinger", False)},
        [line["price"] for line in necklines],
    )
    if y_range is not None:
        fig.update_yaxes(range=y_range)
    fig.update_yaxes(title_text="価格", tickformat=",.0f")
    return fig


def neckline_selection_chart(obs: dict, show: dict[str, bool], necklines: list[dict] | None = None) -> go.Figure:
    return important_price_line_chart(obs, show, necklines)


def important_price_line_chart(
    obs: dict,
    show: dict[str, bool],
    necklines: list[dict] | None = None,
    date_range: tuple[object, object] | None = None,
) -> go.Figure:
    necklines = necklines or []
    daily = _with_daily_axis(long_term_chart_frame(obs["daily_bars"], "日足"))
    visible_daily = _filter_daily_by_date_range(daily, date_range)
    range_start, range_end = _date_range_to_axis_indices(daily, date_range)
    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, None]],
        horizontal_spacing=IMPORTANT_PRICE_HORIZONTAL_SPACING,
        vertical_spacing=0.045,
        column_widths=IMPORTANT_PRICE_COLUMN_WIDTHS,
        row_heights=[0.78, 0.22],
    )
    _add_long_term_price_traces(fig, visible_daily, show, "日足", row=1, col=1)
    y_range = _price_axis_range(
        visible_daily,
        {"daily_ma": show.get("daily_ma", False), "bollinger": show.get("bollinger", False)},
        [line["price"] for line in necklines],
    )
    if y_range is None:
        return fig

    profile = _volume_profile(visible_daily, y_range)
    if profile is not None:
        fig.add_trace(
            go.Bar(
                x=profile["volumes"],
                y=profile["prices"],
                customdata=profile["ranges"],
                width=profile["bin_size"] * 0.86,
                orientation="h",
                name="価格帯別出来高",
                marker=dict(color="rgba(37, 99, 235, 0.38)", line=dict(color="rgba(37, 99, 235, 0.72)", width=1)),
                hovertemplate=(
                    "価格帯 %{customdata[0]:,.1f} - %{customdata[1]:,.1f}円<br>"
                    "出来高 %{x:,.0f}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=2,
        )

    _add_necklines(fig, necklines, row=1, col=1)
    _add_necklines(fig, necklines, row=1, col=2, annotate=False)
    _add_daily_range_indicator(fig, daily, range_start, range_end, row=2, col=1)

    selector_frame = visible_daily.tail(min(len(visible_daily), 120))
    low, high = float(y_range[0]), float(y_range[1])
    steps = 240
    price_grid = [low + ((high - low) * index / steps) for index in range(steps + 1)]
    x_values = []
    y_values = []
    customdata = []
    for date_value in selector_frame["_axis_x"]:
        for price in price_grid:
            x_values.append(date_value)
            y_values.append(price)
            customdata.append([price])

    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            customdata=customdata,
            mode="markers",
            marker=dict(size=14, color="rgba(17, 24, 39, 0.001)"),
            hovertemplate="選択価格 %{y:,.1f}円<extra></extra>",
            name="価格選択",
            showlegend=False,
            selected=dict(marker=dict(color="rgba(17, 24, 39, 0.001)")),
            unselected=dict(marker=dict(opacity=0.001)),
        ),
        row=1,
        col=1,
    )
    fig.update_layout(
        height=760,
        margin=dict(l=10, r=10, t=30, b=36),
        xaxis_rangeslider_visible=False,
        clickmode="event+select",
        dragmode="select",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
    if not visible_daily.empty:
        tick_frame = _daily_tick_frame(visible_daily)
        fig.update_xaxes(
            range=[float(visible_daily["_axis_x"].min()) - 0.5, float(visible_daily["_axis_x"].max()) + 0.5],
            tickmode="array",
            tickvals=tick_frame["_axis_x"],
            ticktext=tick_frame["_axis_label"],
            row=1,
            col=1,
        )
    if not daily.empty:
        indicator_tick_frame = _daily_tick_frame(daily)
        fig.update_xaxes(
            range=[float(daily["_axis_x"].min()) - 0.5, float(daily["_axis_x"].max()) + 0.5],
            tickmode="array",
            tickvals=indicator_tick_frame["_axis_x"],
            ticktext=indicator_tick_frame["_axis_label"],
            showgrid=False,
            zeroline=False,
            title_text="日足表示範囲（下のバーをドラッグして選択）",
            row=2,
            col=1,
        )
    fig.update_xaxes(title_text="価格帯別出来高", tickformat=",d", showgrid=False, row=1, col=2)
    fig.update_yaxes(range=y_range, title_text="価格", tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(range=y_range, showticklabels=False, row=1, col=2)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, range=[-1, 1], row=2, col=1)
    fig.update_yaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikedash="dash",
        spikecolor="#111827",
        spikethickness=1,
        row=1,
        col=1,
    )
    return fig


def intraday_interval_minutes(chart_type: str) -> int:
    if chart_type not in INTRADAY_INTERVALS:
        raise ValueError(f"未対応の分足です: {chart_type}")
    return INTRADAY_INTERVALS[chart_type]


def intraday_chart_frame(minute: pd.DataFrame, chart_type: str) -> pd.DataFrame:
    interval = intraday_interval_minutes(chart_type)
    result = minute.copy().sort_values("timestamp").reset_index(drop=True)
    result["timestamp"] = pd.to_datetime(result["timestamp"])

    if interval == 1:
        result["period_start"] = result["timestamp"]
        result["period_end"] = result["timestamp"]
        return result

    source = result.copy()
    source["_last_timestamp"] = source["timestamp"]
    aggregation = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "_last_timestamp": "last",
    }
    if "vwap" in source:
        aggregation["vwap"] = "last"

    resampled = (
        source.set_index("timestamp")
        .resample(f"{interval}min", origin="start")
        .agg(aggregation)
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
        .rename(columns={"timestamp": "period_start", "_last_timestamp": "timestamp"})
    )
    resampled["period_end"] = resampled["timestamp"]
    resampled["volume"] = resampled["volume"].astype(int)
    resampled["ma_5"] = moving_average(resampled["close"], 5)
    resampled["ma_25"] = moving_average(resampled["close"], 25)
    bands = bollinger_bands(resampled["close"], 20)
    for column in bands.columns:
        resampled[column] = bands[column]
    return resampled


def _volume_bar_colors(frame: pd.DataFrame) -> list[str]:
    colors = []
    for row in frame[["open", "close"]].itertuples(index=False):
        open_price = float(row.open)
        close_price = float(row.close)
        if close_price > open_price:
            colors.append(UP_CANDLE_COLOR)
        elif close_price < open_price:
            colors.append(DOWN_CANDLE_COLOR)
        else:
            colors.append(FLAT_CANDLE_COLOR)
    return colors


def long_term_chart_frame(daily: pd.DataFrame, chart_type: str) -> pd.DataFrame:
    return _higher_timeframe_bars(daily, chart_type)


def _add_long_term_price_traces(
    fig: go.Figure,
    daily: pd.DataFrame,
    show: dict[str, bool],
    chart_type: str,
    row: int | None = None,
    col: int | None = None,
) -> None:
    x_values = daily["_axis_x"] if "_axis_x" in daily else daily["date"]
    date_text = pd.to_datetime(daily["date"]).dt.strftime("%Y-%m-%d")
    customdata = list(zip(date_text, daily["volume"], strict=True))
    _add_trace(
        fig,
        go.Candlestick(
            x=x_values,
            open=daily["open"],
            high=daily["high"],
            low=daily["low"],
            close=daily["close"],
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>"
                "始値 %{open:,.1f}円<br>"
                "高値 %{high:,.1f}円<br>"
                "安値 %{low:,.1f}円<br>"
                "終値 %{close:,.1f}円<br>"
                "出来高 %{customdata[1]:,.0f}<extra></extra>"
            ),
            name=chart_type,
        ),
        row,
        col,
    )
    if show.get("daily_ma"):
        for column, label in [
            ("ma_5", f"{chart_type} 移動平均5"),
            ("ma_25", f"{chart_type} 移動平均25"),
            ("ma_75", f"{chart_type} 移動平均75"),
        ]:
            _add_trace(fig, go.Scatter(x=x_values, y=daily[column], name=label, line=dict(width=1.3)), row, col)
    if show.get("bollinger"):
        for column, label, color in BOLLINGER_STYLES:
            _add_trace(
                fig,
                go.Scatter(
                    x=x_values,
                    y=daily[column],
                    name=f"{chart_type} ボリンジャー {label}",
                    line=dict(width=1.0, dash="dot", color=color),
                ),
                row,
                col,
            )


def _add_trace(fig: go.Figure, trace: go.BaseTraceType, row: int | None = None, col: int | None = None) -> None:
    if row is not None and col is not None:
        fig.add_trace(trace, row=row, col=col)
    else:
        fig.add_trace(trace)


def _volume_profile(frame: pd.DataFrame, y_range: list[float], bins: int = 32) -> dict[str, list] | None:
    if frame.empty or bins <= 0:
        return None

    low, high = float(y_range[0]), float(y_range[1])
    if high <= low:
        return None

    bin_size = (high - low) / bins
    volumes = [0.0] * bins
    for row in frame.dropna(subset=["low", "high", "volume"]).itertuples():
        row_low = max(float(row.low), low)
        row_high = min(float(row.high), high)
        volume = float(row.volume)
        if volume <= 0 or row_high < low or row_low > high:
            continue
        if row_high <= row_low:
            index = min(max(int((row_low - low) / bin_size), 0), bins - 1)
            volumes[index] += volume
            continue
        first = min(max(int((row_low - low) / bin_size), 0), bins - 1)
        last = min(max(int((row_high - low) / bin_size), 0), bins - 1)
        share = volume / max(last - first + 1, 1)
        for index in range(first, last + 1):
            volumes[index] += share

    if not any(volumes):
        return None

    prices = [low + (index + 0.5) * bin_size for index in range(bins)]
    ranges = [[low + index * bin_size, low + (index + 1) * bin_size] for index in range(bins)]
    return {"prices": prices, "volumes": volumes, "ranges": ranges, "bin_size": bin_size}


def _date_range_to_axis_indices(frame: pd.DataFrame, date_range: tuple[object, object] | None) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    if date_range is None or len(date_range) != 2:
        return int(frame["_axis_x"].min()), int(frame["_axis_x"].max())

    if all(isinstance(value, int) for value in date_range):
        start, end = sorted((int(date_range[0]), int(date_range[1])))
        return max(start, 0), min(end, len(frame) - 1)

    dates = pd.to_datetime(frame["date"])
    start_date, end_date = sorted(pd.to_datetime([date_range[0], date_range[1]]))
    selected = frame[(dates >= start_date) & (dates <= end_date)]
    if selected.empty:
        return int(frame["_axis_x"].min()), int(frame["_axis_x"].max())
    return int(selected["_axis_x"].min()), int(selected["_axis_x"].max())


def _add_daily_range_indicator(
    fig: go.Figure,
    daily: pd.DataFrame,
    start_index: int,
    end_index: int,
    row: int,
    col: int,
) -> None:
    if daily.empty:
        return

    start_index, end_index = sorted((int(start_index), int(end_index)))
    start_index = max(start_index, int(daily["_axis_x"].min()))
    end_index = min(end_index, int(daily["_axis_x"].max()))
    full_start = float(daily["_axis_x"].min()) - 0.5
    full_end = float(daily["_axis_x"].max()) + 0.5
    selected_start = float(start_index) - 0.5
    selected_end = float(end_index) + 0.5

    fig.add_shape(
        type="rect",
        x0=full_start,
        x1=full_end,
        y0=-0.46,
        y1=0.46,
        fillcolor="rgba(148, 163, 184, 0.30)",
        line=dict(color="rgba(100, 116, 139, 0.65)", width=1),
        layer="below",
        row=row,
        col=col,
    )
    fig.add_shape(
        type="rect",
        x0=selected_start,
        x1=selected_end,
        y0=-0.50,
        y1=0.50,
        fillcolor="rgba(37, 99, 235, 0.82)",
        line=dict(color="#1d4ed8", width=2),
        layer="below",
        row=row,
        col=col,
    )

    fig.add_trace(
        go.Scatter(
            x=[daily["_axis_x"].min(), daily["_axis_x"].max()],
            y=[0, 0],
            mode="lines",
            line=dict(color="rgba(148, 163, 184, 0.88)", width=5),
            hoverinfo="skip",
            showlegend=False,
            name="日足表示範囲全体",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[start_index, end_index],
            y=[0, 0],
            mode="lines",
            line=dict(color="#1d4ed8", width=8),
            customdata=[["range-indicator"], ["range-indicator"]],
            hovertemplate="表示範囲<extra></extra>",
            showlegend=False,
            name="日足表示範囲",
        ),
        row=row,
        col=col,
    )
    date_text = pd.to_datetime(daily["date"]).dt.strftime("%Y-%m-%d")
    fig.add_trace(
        go.Scatter(
            x=daily["_axis_x"],
            y=[0] * len(daily),
            mode="markers",
            marker=dict(size=22, color="rgba(37, 99, 235, 0.30)", line=dict(color="rgba(255, 255, 255, 0.85)", width=0.7)),
            customdata=[
                ["range-selector", int(axis_x), date_label]
                for axis_x, date_label in zip(daily["_axis_x"], date_text, strict=True)
            ],
            hovertemplate="%{customdata[2]}<extra>日足表示範囲</extra>",
            showlegend=False,
            name="日足表示範囲調整",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[start_index, end_index],
            y=[0, 0],
            mode="markers",
            marker=dict(size=18, symbol="square", color="#1d4ed8", line=dict(color="#ffffff", width=2.4)),
            customdata=[["range-indicator"], ["range-indicator"]],
            hovertemplate="表示範囲<extra></extra>",
            showlegend=False,
            name="日足表示範囲の端",
        ),
        row=row,
        col=col,
    )


def _filter_daily_by_date_range(frame: pd.DataFrame, date_range: tuple[object, object] | None) -> pd.DataFrame:
    if frame.empty or date_range is None or len(date_range) != 2:
        return frame

    if all(isinstance(value, int) for value in date_range):
        start, end = sorted((int(date_range[0]), int(date_range[1])))
        start = max(start, 0)
        end = min(end, len(frame) - 1)
        result = frame.iloc[start : end + 1].copy()
        if result.empty:
            return frame.tail(min(len(frame), 120)).copy()
        return result

    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    result = frame[(pd.to_datetime(frame["date"]) >= start) & (pd.to_datetime(frame["date"]) <= end)].copy()
    if result.empty:
        return frame.tail(min(len(frame), 120)).copy()
    return result


def _with_daily_axis(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy().reset_index(drop=True)
    result["_axis_x"] = list(range(len(result)))
    result["_axis_label"] = pd.to_datetime(result["date"]).dt.strftime("%m/%d")
    return result


def _daily_tick_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    stride = max(len(frame) // 8, 1)
    return frame.iloc[::stride][["_axis_x", "_axis_label"]]


def _latest_known_daily(daily: pd.DataFrame) -> pd.Series | None:
    if daily.empty:
        return None
    return daily.iloc[-1]


def _previous_day_context_x(
    visible_minute: pd.DataFrame,
    x_range: list[float] | None,
    interval_minutes: int,
    previous: pd.Series | None,
) -> float | None:
    if previous is None or visible_minute.empty:
        return None
    if float(visible_minute["chart_x"].min()) > 0:
        return None
    if x_range is not None:
        return float(x_range[0]) + max(float(interval_minutes), 1.0) * 0.8
    return -max(float(interval_minutes), 1.0)


def _expand_price_axis_range(price_range: list[float], prices: list[float]) -> list[float]:
    values = [float(price_range[0]), float(price_range[1]), *[float(price) for price in prices]]
    low = min(values)
    high = max(values)
    if low == high:
        padding = max(abs(low) * 0.01, 1.0)
    else:
        padding = (high - low) * 0.08
    return [low - padding, high + padding]


def _visible_minute_bars(
    minute: pd.DataFrame,
    display_window: str,
    interval_minutes: int,
) -> tuple[pd.DataFrame, list[float] | None]:
    if display_window == "全表示":
        return minute, None

    minutes = int(display_window.replace("過去", "").replace("前後", "").replace("分", ""))
    current_x = float(minute["chart_x"].iloc[-1])
    right_padding = round(max(float(interval_minutes) * 2.0, float(minutes) * 0.12), 6)
    start_x = current_x - minutes
    end_x = current_x + right_padding
    visible = minute[(minute["chart_x"] >= start_x) & (minute["chart_x"] <= current_x)].copy()
    if visible.empty:
        visible = minute.tail(1).copy()
    return visible, [start_x, end_x]


def _higher_timeframe_bars(daily: pd.DataFrame, chart_type: str) -> pd.DataFrame:
    result = daily.copy()
    result["date"] = pd.to_datetime(result["date"])
    if chart_type == "日足":
        result = result.rename(
            columns={
                "daily_ma_5": "ma_5",
                "daily_ma_25": "ma_25",
                "daily_ma_75": "ma_75",
            }
        )
        bands = bollinger_bands(result["close"], 20)
        for column in bands.columns:
            result[column] = bands[column]
        return result

    rule = "W-FRI" if chart_type == "週足" else "ME"
    resampled = (
        result.set_index("date")
        .resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    resampled["ma_5"] = resampled["close"].rolling(window=5, min_periods=1).mean()
    resampled["ma_25"] = resampled["close"].rolling(window=25, min_periods=1).mean()
    resampled["ma_75"] = resampled["close"].rolling(window=75, min_periods=1).mean()
    bands = bollinger_bands(resampled["close"], 20)
    for column in bands.columns:
        resampled[column] = bands[column]
    return resampled


def _with_compressed_x(minute: pd.DataFrame, interval_minutes: int) -> pd.DataFrame:
    result = minute.copy()
    timestamps = pd.to_datetime(result.get("period_start", result["timestamp"]))
    positions = [0.0]
    for previous, current in zip(timestamps.iloc[:-1], timestamps.iloc[1:]):
        expected_step = max(float(interval_minutes), 1.0)
        positions.append(positions[-1] + expected_step)
    result["chart_x"] = positions
    return result


def _time_ticks(minute: pd.DataFrame) -> tuple[list[float], list[str]]:
    if minute.empty:
        return [], []
    stride = max(len(minute) // 8, 1)
    tick_frame = minute.iloc[::stride]
    return tick_frame["chart_x"].astype(float).tolist(), tick_frame["timestamp"].dt.strftime("%H:%M").tolist()


def _add_trade_markers(fig: go.Figure, visible_minute: pd.DataFrame, fills: list[dict]) -> None:
    if not fills or visible_minute.empty:
        return

    visible_lookup = {
        pd.Timestamp(row.timestamp): (float(row.chart_x), (float(row.open) + float(row.close)) / 2.0)
        for row in visible_minute.itertuples()
    }
    marker_groups = {
        "long_in": {"x": [], "y": [], "text": [], "name": "買い建て", "color": "#0f9d58", "symbol": "triangle-up"},
        "long_out": {"x": [], "y": [], "text": [], "name": "買い決済", "color": "#2563eb", "symbol": "circle"},
        "short_in": {"x": [], "y": [], "text": [], "name": "空売り建て", "color": "#dc2626", "symbol": "triangle-down"},
        "short_out": {"x": [], "y": [], "text": [], "name": "空売り決済", "color": "#f59e0b", "symbol": "diamond"},
    }

    for fill in fills:
        timestamp = pd.Timestamp(fill["timestamp"])
        if timestamp in visible_lookup:
            x_value, body_midpoint = visible_lookup[timestamp]
        else:
            matched = visible_minute[
                (pd.to_datetime(visible_minute.get("period_start", visible_minute["timestamp"])) <= timestamp)
                & (pd.to_datetime(visible_minute.get("period_end", visible_minute["timestamp"])) >= timestamp)
            ]
            if matched.empty:
                continue
            row = matched.iloc[-1]
            x_value = float(row["chart_x"])
            body_midpoint = (float(row["open"]) + float(row["close"])) / 2.0
        if pd.isna(x_value) or pd.isna(body_midpoint):
            continue
        side = fill.get("side")
        action = fill.get("action")
        if action == "OPEN" and side == "LONG":
            key, text = "long_in", "買建"
        elif action == "CLOSE" and side == "LONG":
            key, text = "long_out", "決済"
        elif action == "OPEN" and side == "SHORT":
            key, text = "short_in", "空売"
        elif action == "CLOSE" and side == "SHORT":
            key, text = "short_out", "買戻"
        else:
            continue
        group = marker_groups[key]
        group["x"].append(x_value)
        group["y"].append(body_midpoint)
        group["text"].append(text)

    for group in marker_groups.values():
        if not group["x"]:
            continue
        fig.add_trace(
            go.Scatter(
                x=group["x"],
                y=group["y"],
                mode="markers+text",
                name=group["name"],
                text=group["text"],
                textposition="top center",
                marker=dict(size=15, color=group["color"], symbol=group["symbol"], line=dict(width=2, color="#111827")),
            ),
            row=1,
            col=1,
        )


def _add_necklines(
    fig: go.Figure,
    necklines: list[dict],
    row: int | None = None,
    col: int | None = None,
    annotate: bool = True,
) -> None:
    for line in necklines:
        price = float(line["price"])
        label = str(line.get("label") or "重要価格ライン")
        color = str(line.get("color") or "#7c3aed")
        kwargs = {
            "y": price,
            "line_width": 2,
            "line_dash": "dash",
            "line_color": color,
        }
        if annotate:
            kwargs["annotation_text"] = f"{label} {price:,.1f}円"
            kwargs["annotation_position"] = "top right"
        if row is not None and col is not None:
            kwargs["row"] = row
            kwargs["col"] = col
        fig.add_hline(**kwargs)


def _price_axis_range(frame: pd.DataFrame, show: dict[str, bool], extra_prices: list[float] | None = None) -> list[float] | None:
    if frame.empty:
        return None
    columns = ["high", "low"]
    if show.get("vwap"):
        columns.append("vwap")
    if show.get("minute_ma"):
        columns.extend(["ma_5", "ma_25"])
    if show.get("bollinger"):
        columns.extend(["bb_upper_1", "bb_lower_1", "bb_upper_2", "bb_lower_2", "bb_upper_3", "bb_lower_3"])
    if show.get("daily_ma"):
        columns.extend(["ma_5", "ma_25", "ma_75"])

    values = []
    for column in columns:
        if column in frame:
            values.extend(frame[column].dropna().astype(float).tolist())
    if extra_prices:
        values.extend(float(price) for price in extra_prices)
    if not values:
        return None

    low = min(values)
    high = max(values)
    if low == high:
        padding = max(abs(low) * 0.01, 1.0)
    else:
        padding = (high - low) * 0.08
    return [low - padding, high + padding]


def _intraday_price_axis_range(
    frame: pd.DataFrame,
    show: dict[str, bool],
    extra_prices: list[float] | None = None,
) -> list[float] | None:
    if frame.empty:
        return None

    candle_values = frame[["high", "low"]].dropna().astype(float)
    if candle_values.empty:
        return None

    base_low = float(candle_values["low"].min())
    base_high = float(candle_values["high"].max())
    center = (base_low + base_high) / 2.0
    min_span = max(abs(center) * 0.0015, 1.0)
    base_span = max(base_high - base_low, min_span)
    include_low = base_low - base_span * 0.25
    include_high = base_high + base_span * 0.25
    values = [base_low, base_high]

    for column in _visible_indicator_columns(show):
        if column not in frame:
            continue
        for value in frame[column].dropna().astype(float):
            if include_low <= value <= include_high:
                values.append(float(value))

    if extra_prices:
        for price in extra_prices:
            value = float(price)
            if include_low <= value <= include_high:
                values.append(value)

    low = min(values)
    high = max(values)
    span = max(high - low, min_span)
    center = (low + high) / 2.0
    padding = span * 0.10
    return [center - (span / 2.0) - padding, center + (span / 2.0) + padding]


def _visible_indicator_columns(show: dict[str, bool]) -> list[str]:
    columns = []
    if show.get("vwap"):
        columns.append("vwap")
    if show.get("minute_ma"):
        columns.extend(["ma_5", "ma_25"])
    if show.get("bollinger"):
        columns.extend(["bb_upper_1", "bb_lower_1", "bb_upper_2", "bb_lower_2", "bb_upper_3", "bb_lower_3"])
    return columns
