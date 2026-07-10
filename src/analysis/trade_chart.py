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
TRADE_RULES = [
    "1 IN Long: body breaks above VWAP/MA",
    "2 IN Short: body breaks below VWAP/MA",
    "3 OUT Long: opposite body break below VWAP/MA",
    "4 OUT Short: opposite body break above VWAP/MA",
    "5 OUT Stop loss",
    "6 OUT Take profit",
    "7 OUT Time/risk/trailing exit",
]
NORMAL_STOP_LOSS_PCT = 0.005
NORMAL_TAKE_PROFIT_PCT = 0.010
FORCE_EXIT_TIME = "14:50"


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
    for trade_number, trade in enumerate(trades.itertuples(index=False), start=1):
        side = str(trade.side)
        fills.append(
            {
                "trade_number": trade_number,
                "timestamp": pd.Timestamp(trade.entry_time),
                "action": "OPEN",
                "side": side,
                "quantity": int(trade.quantity),
                "price": float(trade.entry_price),
            }
        )
        fills.append(
            {
                "trade_number": trade_number,
                "timestamp": pd.Timestamp(trade.exit_time),
                "action": "CLOSE",
                "side": side,
                "quantity": int(trade.quantity),
                "entry_price": float(trade.entry_price),
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
    fig.subplots_adjust(right=0.76)
    _draw_candles(price_ax, frame)
    _draw_indicators(price_ax, frame)
    _draw_previous_day_lines(price_ax, daily)
    _draw_trade_markers(price_ax, frame, fills, strategy_name=strategy_name)
    _draw_rule_panel(price_ax)
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
        ("ma_75", "MA75", "#0891b2", "-", 0.9),
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


def _draw_trade_markers(ax: plt.Axes, frame: pd.DataFrame, fills: list[dict], *, strategy_name: str) -> None:
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
    stacked_offsets: dict[tuple[pd.Timestamp, str], int] = {}
    for fill in fills:
        timestamp = pd.Timestamp(fill["timestamp"])
        x_value = x_by_timestamp.get(timestamp)
        if x_value is None:
            continue
        key = (str(fill.get("action")), str(fill.get("side")))
        if key not in marker_styles:
            continue
        marker, color, label = marker_styles[key]
        row = frame.loc[int(x_value)]
        price = (float(row.open) + float(row.close)) / 2
        legend_label = label if key not in labeled_keys else None
        labeled_keys.add(key)
        ax.scatter(
            [x_value],
            [price],
            marker=marker,
            s=42,
            color=color,
            edgecolors="#111827",
            linewidths=0.7,
            zorder=5,
            label=legend_label,
        )
        slot_key = (timestamp, str(fill.get("action")))
        slot = stacked_offsets.get(slot_key, 0)
        stacked_offsets[slot_key] = slot + 1
        rule_id = _rule_id_for_fill(fill, strategy_name=strategy_name)
        _annotate_rule_id(ax, x_value, price, key, slot, rule_id)
        if key[0] == "CLOSE" and "pnl" in fill:
            _annotate_exit_pnl(ax, x_value, price, key, slot, float(fill["pnl"]))


def _draw_rule_panel(ax: plt.Axes) -> None:
    ax.text(
        1.015,
        0.98,
        "Trade rules\n" + "\n".join(TRADE_RULES),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        color="#111827",
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#cbd5e1",
            "alpha": 0.94,
        },
        clip_on=False,
        zorder=7,
    )


def _annotate_rule_id(
    ax: plt.Axes,
    x_value: float,
    price: float,
    key: tuple[str, str],
    slot: int,
    rule_id: str,
) -> None:
    dx, dy = _rule_offset(key, slot)
    ax.annotate(
        rule_id,
        xy=(x_value, price),
        xytext=(dx, dy),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=6.5,
        color="#111827",
        bbox={
            "boxstyle": "circle,pad=0.18",
            "facecolor": "white",
            "edgecolor": "#111827",
            "linewidth": 0.55,
            "alpha": 0.96,
        },
        arrowprops={"arrowstyle": "-", "color": "#64748b", "linewidth": 0.45, "shrinkA": 1.5, "shrinkB": 2.0},
        clip_on=False,
        zorder=8,
    )


def _annotate_exit_pnl(ax: plt.Axes, x_value: float, price: float, key: tuple[str, str], slot: int, pnl: float) -> None:
    dx, dy = _pnl_offset(key, slot)
    color = "#dc2626" if pnl >= 0 else "#16a34a"
    ax.annotate(
        f"PnL {_format_signed_yen(pnl)}",
        xy=(x_value, price),
        xytext=(dx, dy),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=6.8,
        color=color,
        bbox={
            "boxstyle": "round,pad=0.18",
            "facecolor": "white",
            "edgecolor": color,
            "linewidth": 0.55,
            "alpha": 0.94,
        },
        clip_on=False,
        zorder=8,
    )


def _rule_offset(key: tuple[str, str], slot: int) -> tuple[float, float]:
    base_offsets = {
        ("OPEN", "LONG"): (-9, 16),
        ("CLOSE", "LONG"): (9, -16),
        ("OPEN", "SHORT"): (-9, -16),
        ("CLOSE", "SHORT"): (9, 16),
    }
    dx, dy = base_offsets.get(key, (9, 16))
    direction = 1 if dy >= 0 else -1
    return dx + (slot * 8), dy + (slot * 8 * direction)


def _pnl_offset(key: tuple[str, str], slot: int) -> tuple[float, float]:
    base_offsets = {
        ("CLOSE", "LONG"): (34, -28),
        ("CLOSE", "SHORT"): (34, 28),
    }
    dx, dy = base_offsets.get(key, (34, 28))
    direction = 1 if dy >= 0 else -1
    return dx + (slot * 10), dy + (slot * 9 * direction)


def _rule_id_for_fill(fill: dict, *, strategy_name: str) -> str:
    action = str(fill.get("action"))
    side = str(fill.get("side"))
    if action == "OPEN":
        return "1" if side == "LONG" else "2"
    if action != "CLOSE":
        return "7"
    if _is_force_exit(fill):
        return "7"
    if _is_stop_loss(fill, strategy_name=strategy_name):
        return "5"
    if _is_take_profit(fill, strategy_name=strategy_name):
        return "6"
    return "3" if side == "LONG" else "4"


def _is_force_exit(fill: dict) -> bool:
    return pd.Timestamp(fill["timestamp"]).strftime("%H:%M") >= FORCE_EXIT_TIME


def _is_stop_loss(fill: dict, *, strategy_name: str) -> bool:
    entry_price = float(fill.get("entry_price", fill.get("price", 0.0)))
    exit_price = float(fill.get("price", 0.0))
    side = str(fill.get("side"))
    stop_loss_pct, _ = _risk_thresholds(strategy_name)
    if entry_price <= 0:
        return False
    if side == "LONG":
        return exit_price <= entry_price * (1 - stop_loss_pct)
    return exit_price >= entry_price * (1 + stop_loss_pct)


def _is_take_profit(fill: dict, *, strategy_name: str) -> bool:
    entry_price = float(fill.get("entry_price", fill.get("price", 0.0)))
    exit_price = float(fill.get("price", 0.0))
    side = str(fill.get("side"))
    _, take_profit_pct = _risk_thresholds(strategy_name)
    if entry_price <= 0:
        return False
    if side == "LONG":
        return exit_price >= entry_price * (1 + take_profit_pct)
    return exit_price <= entry_price * (1 - take_profit_pct)


def _risk_thresholds(strategy_name: str) -> tuple[float, float]:
    if strategy_name == "combined_low_risk":
        return 0.004, 0.007
    if strategy_name == "combined_high_risk":
        return 0.006, 0.014
    if strategy_name == "multi_timeframe_bb3_reversion":
        return 0.005, 0.009
    return NORMAL_STOP_LOSS_PCT, NORMAL_TAKE_PROFIT_PCT


def _format_signed_yen(value: float) -> str:
    return f"{value:+,.0f}"


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
