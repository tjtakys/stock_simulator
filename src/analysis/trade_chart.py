from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.indicators.registry import add_daily_indicators, add_minute_indicators


UP_COLOR = "#dc2626"
DOWN_COLOR = "#16a34a"
DOJI_COLOR = "#64748b"


def write_trade_chart(
    path: Path,
    *,
    symbol: str,
    trading_date: str,
    strategy_name: str,
    minute: pd.DataFrame,
    daily: pd.DataFrame,
    trades: pd.DataFrame,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    minute_frame = add_minute_indicators(minute.sort_values("timestamp").reset_index(drop=True))
    daily_frame = add_daily_indicators(daily.sort_values("date").reset_index(drop=True))
    _write_png_chart(
        path,
        symbol=symbol,
        trading_date=trading_date,
        strategy_name=strategy_name,
        minute=minute_frame,
        daily=daily_frame,
        fills=fills_from_trades(trades),
    )
    return path


def fills_from_trades(trades: pd.DataFrame) -> list[dict]:
    if trades.empty:
        return []

    fills: list[dict] = []
    for trade in trades.itertuples(index=False):
        side = str(trade.side)
        fills.append(
            {
                "timestamp": pd.Timestamp(trade.entry_time),
                "action": "OPEN",
                "side": side,
                "quantity": int(trade.quantity),
                "price": float(trade.entry_price),
            }
        )
        fills.append(
            {
                "timestamp": pd.Timestamp(trade.exit_time),
                "action": "CLOSE",
                "side": side,
                "quantity": int(trade.quantity),
                "price": float(trade.exit_price),
                "pnl": float(trade.pnl),
            }
        )
    return fills


def _write_png_chart(
    path: Path,
    *,
    symbol: str,
    trading_date: str,
    strategy_name: str,
    minute: pd.DataFrame,
    daily: pd.DataFrame,
    fills: list[dict],
) -> None:
    frame = minute.copy().reset_index(drop=True)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["chart_x"] = range(len(frame))

    fig, (price_ax, volume_ax) = plt.subplots(
        2,
        1,
        figsize=(18, 10),
        gridspec_kw={"height_ratios": [3.2, 1.0], "hspace": 0.06},
        sharex=True,
    )
    fig.patch.set_facecolor("white")
    _draw_candles(price_ax, frame)
    _draw_indicators(price_ax, frame)
    _draw_previous_day_lines(price_ax, daily)
    _draw_trade_markers(price_ax, frame, fills)
    price_ax.legend(loc="upper left", ncols=4, fontsize=8, frameon=False)
    _draw_volume(volume_ax, frame)
    _format_axes(price_ax, volume_ax, frame)
    price_ax.set_title(f"{symbol} {trading_date} {strategy_name}", loc="left", fontsize=14, pad=12)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _draw_candles(ax: plt.Axes, frame: pd.DataFrame) -> None:
    width = 0.62
    for row in frame.itertuples(index=False):
        x_value = float(row.chart_x)
        open_price = float(row.open)
        high_price = float(row.high)
        low_price = float(row.low)
        close_price = float(row.close)
        color = _candle_color(open_price, close_price)
        ax.vlines(x_value, low_price, high_price, color=color, linewidth=0.8, alpha=0.95)
        lower = min(open_price, close_price)
        height = abs(close_price - open_price)
        if height == 0:
            ax.hlines(close_price, x_value - width / 2, x_value + width / 2, color=color, linewidth=1.1)
        else:
            ax.add_patch(
                Rectangle(
                    (x_value - width / 2, lower),
                    width,
                    height,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=0.6,
                    alpha=0.56,
                )
            )


def _draw_indicators(ax: plt.Axes, frame: pd.DataFrame) -> None:
    styles = [
        ("vwap", "VWAP", "#2563eb", "-", 1.25),
        ("ma_5", "MA5", "#f59e0b", "-", 1.0),
        ("ma_25", "MA25", "#7c3aed", "-", 1.0),
        ("bb_upper_2", "BB +2σ", "#94a3b8", "--", 0.8),
        ("bb_lower_2", "BB -2σ", "#94a3b8", "--", 0.8),
        ("bb_upper_3", "BB +3σ", "#64748b", ":", 0.8),
        ("bb_lower_3", "BB -3σ", "#64748b", ":", 0.8),
    ]
    for column, label, color, linestyle, linewidth in styles:
        if column in frame:
            values = pd.to_numeric(frame[column], errors="coerce").astype(float).to_numpy()
            ax.plot(frame["chart_x"], values, label=label, color=color, linestyle=linestyle, linewidth=linewidth)


def _draw_previous_day_lines(ax: plt.Axes, daily: pd.DataFrame) -> None:
    if daily.empty:
        return
    previous = daily.iloc[-1]
    for column, label in [("high", "Prev High"), ("low", "Prev Low"), ("close", "Prev Close")]:
        ax.axhline(float(previous[column]), color="#94a3b8", linestyle="--", linewidth=0.8)
        ax.text(0.995, float(previous[column]), label, transform=ax.get_yaxis_transform(), ha="right", va="bottom", fontsize=8)


def _draw_trade_markers(ax: plt.Axes, frame: pd.DataFrame, fills: list[dict]) -> None:
    if not fills:
        return
    x_by_timestamp = {pd.Timestamp(row.timestamp): float(row.chart_x) for row in frame.itertuples(index=False)}
    marker_styles = {
        ("OPEN", "LONG"): ("^", "#0f9d58", "Long In"),
        ("CLOSE", "LONG"): ("o", "#2563eb", "Long Out"),
        ("OPEN", "SHORT"): ("v", "#dc2626", "Short In"),
        ("CLOSE", "SHORT"): ("D", "#f59e0b", "Short Out"),
    }
    labeled_keys: set[tuple[str, str]] = set()
    for fill in fills:
        timestamp = pd.Timestamp(fill["timestamp"])
        x_value = x_by_timestamp.get(timestamp)
        if x_value is None:
            continue
        key = (str(fill.get("action")), str(fill.get("side")))
        if key not in marker_styles:
            continue
        marker, color, label = marker_styles[key]
        price = float(fill.get("price", frame.loc[int(x_value), "close"]))
        legend_label = label if key not in labeled_keys else None
        labeled_keys.add(key)
        ax.scatter(
            [x_value],
            [price],
            marker=marker,
            s=88,
            color=color,
            edgecolors="#111827",
            linewidths=0.9,
            zorder=5,
            label=legend_label,
        )


def _draw_volume(ax: plt.Axes, frame: pd.DataFrame) -> None:
    colors = [_candle_color(float(row.open), float(row.close)) for row in frame.itertuples(index=False)]
    volume = pd.to_numeric(frame["volume"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    ax.bar(frame["chart_x"], volume, width=0.72, color=colors, alpha=0.42)


def _format_axes(price_ax: plt.Axes, volume_ax: plt.Axes, frame: pd.DataFrame) -> None:
    for ax in [price_ax, volume_ax]:
        ax.grid(True, color="#e5e7eb", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    price_ax.set_ylabel("Price")
    volume_ax.set_ylabel("Volume")
    volume_ax.set_xlabel("Time")
    tick_count = min(10, len(frame))
    tick_indexes = sorted(set(round(i * (len(frame) - 1) / max(tick_count - 1, 1)) for i in range(tick_count)))
    volume_ax.set_xticks(tick_indexes)
    volume_ax.set_xticklabels(frame.loc[tick_indexes, "timestamp"].dt.strftime("%H:%M"), rotation=0)
    price_ax.margins(x=0.01)
    volume_ax.margins(x=0.01)


def _candle_color(open_price: float, close_price: float) -> str:
    if close_price > open_price:
        return UP_COLOR
    if close_price < open_price:
        return DOWN_COLOR
    return DOJI_COLOR
