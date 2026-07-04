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
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.72, 0.28],
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
    fig.add_trace(go.Bar(x=visible_minute["chart_x"], y=visible_minute["volume"], name="出来高"), row=2, col=1)

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
        for column, label in [
            ("bb_upper_1", "+1σ"),
            ("bb_lower_1", "-1σ"),
            ("bb_upper_2", "+2σ"),
            ("bb_lower_2", "-2σ"),
            ("bb_upper_3", "+3σ"),
            ("bb_lower_3", "-3σ"),
        ]:
            fig.add_trace(
                go.Scatter(
                    x=visible_minute["chart_x"],
                    y=visible_minute[column],
                    name=f"ボリンジャー {label}",
                    line=dict(width=0.9, dash="dot"),
                ),
                row=1,
                col=1,
            )

    _add_trade_markers(fig, visible_minute, obs.get("fills", []))

    previous = _latest_known_daily(daily)
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
    y_range = _price_axis_range(visible_minute, show, [line["price"] for line in necklines])
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
    fig.add_trace(
        go.Candlestick(
            x=daily["date"],
            open=daily["open"],
            high=daily["high"],
            low=daily["low"],
            close=daily["close"],
            customdata=daily["volume"],
            hovertemplate=(
                "%{x|%Y-%m-%d}<br>"
                "始値 %{open:,.1f}円<br>"
                "高値 %{high:,.1f}円<br>"
                "安値 %{low:,.1f}円<br>"
                "終値 %{close:,.1f}円<br>"
                "出来高 %{customdata:,.0f}<extra></extra>"
            ),
            name=chart_type,
        )
    )
    if show.get("daily_ma"):
        for column, label in [
            ("ma_5", f"{chart_type} 移動平均5"),
            ("ma_25", f"{chart_type} 移動平均25"),
            ("ma_75", f"{chart_type} 移動平均75"),
        ]:
            fig.add_trace(go.Scatter(x=daily["date"], y=daily[column], name=label, line=dict(width=1.3)))
    if show.get("bollinger"):
        for column, label in [
            ("bb_upper_1", "+1σ"),
            ("bb_lower_1", "-1σ"),
            ("bb_upper_2", "+2σ"),
            ("bb_lower_2", "-2σ"),
            ("bb_upper_3", "+3σ"),
            ("bb_lower_3", "-3σ"),
        ]:
            fig.add_trace(
                go.Scatter(
                    x=daily["date"],
                    y=daily[column],
                    name=f"{chart_type} ボリンジャー {label}",
                    line=dict(width=0.9, dash="dot"),
                )
            )
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
    necklines = necklines or []
    fig = daily_chart(obs, show, "日足", necklines)
    daily = long_term_chart_frame(obs["daily_bars"], "日足")
    y_range = _price_axis_range(
        daily,
        {"daily_ma": show.get("daily_ma", False), "bollinger": show.get("bollinger", False)},
        [line["price"] for line in necklines],
    )
    if y_range is None:
        return fig

    selector_frame = daily.tail(min(len(daily), 120))
    low, high = float(y_range[0]), float(y_range[1])
    steps = 240
    price_grid = [low + ((high - low) * index / steps) for index in range(steps + 1)]
    x_values = []
    y_values = []
    customdata = []
    for date_value in selector_frame["date"]:
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
        )
    )
    fig.update_layout(clickmode="event+select", dragmode="pan", hovermode="closest")
    fig.update_yaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikedash="dash",
        spikecolor="#111827",
        spikethickness=1,
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


def long_term_chart_frame(daily: pd.DataFrame, chart_type: str) -> pd.DataFrame:
    return _higher_timeframe_bars(daily, chart_type)


def _latest_known_daily(daily: pd.DataFrame) -> pd.Series | None:
    if daily.empty:
        return None
    return daily.iloc[-1]


def _visible_minute_bars(
    minute: pd.DataFrame,
    display_window: str,
    interval_minutes: int,
) -> tuple[pd.DataFrame, list[float] | None]:
    if display_window == "全表示":
        return minute, None

    minutes = int(display_window.replace("過去", "").replace("前後", "").replace("分", ""))
    current_x = float(minute["chart_x"].iloc[-1])
    min_x = float(minute["chart_x"].min())
    start_x = max(min_x, current_x - minutes)
    end_x = current_x if current_x > start_x else current_x + max(float(interval_minutes), 1.0)
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
        gap_minutes = max((current - previous).total_seconds() / 60.0, 1.0)
        expected_step = max(float(interval_minutes), 1.0)
        step = expected_step + 6.0 if gap_minutes > max(expected_step * 1.5, 5.0) else expected_step
        positions.append(positions[-1] + step)
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


def _add_necklines(fig: go.Figure, necklines: list[dict], row: int | None = None, col: int | None = None) -> None:
    for line in necklines:
        price = float(line["price"])
        label = str(line.get("label") or "ネックライン")
        color = str(line.get("color") or "#7c3aed")
        kwargs = {
            "y": price,
            "line_width": 2,
            "line_dash": "dash",
            "line_color": color,
            "annotation_text": f"{label} {price:,.1f}円",
            "annotation_position": "top right",
        }
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
