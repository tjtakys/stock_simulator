from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd

from src.config import DEFAULT_INITIAL_CASH
from src.indicators.bollinger import bollinger_bands
from src.simulator.order import Action
from src.simulator.position import PositionSide
from src.strategies.base import Strategy


@dataclass(frozen=True)
class StrategyConfig:
    mode: str
    stop_loss_pct: float
    take_profit_pct: float
    break_even_trigger_pct: float
    trailing_start_pct: float
    max_daily_loss_pct: float
    max_trades_per_day: int | None
    max_consecutive_losses: int
    allow_short: bool
    allow_averaging_down: bool
    entry_start_time: str = "09:05"
    entry_end_time: str = "14:45"
    force_exit_time: str = "14:50"


LOW_RISK_CONFIG = StrategyConfig(
    mode="combined_low_risk",
    stop_loss_pct=0.004,
    take_profit_pct=0.007,
    break_even_trigger_pct=0.005,
    trailing_start_pct=0.006,
    max_daily_loss_pct=0.008,
    max_trades_per_day=5,
    max_consecutive_losses=3,
    allow_short=False,
    allow_averaging_down=False,
)

NORMAL_CONFIG = StrategyConfig(
    mode="combined_normal",
    stop_loss_pct=0.005,
    take_profit_pct=0.010,
    break_even_trigger_pct=0.006,
    trailing_start_pct=0.007,
    max_daily_loss_pct=0.015,
    max_trades_per_day=None,
    max_consecutive_losses=3,
    allow_short=True,
    allow_averaging_down=False,
)

HIGH_RISK_CONFIG = StrategyConfig(
    mode="combined_high_risk",
    stop_loss_pct=0.006,
    take_profit_pct=0.014,
    break_even_trigger_pct=0.008,
    trailing_start_pct=0.008,
    max_daily_loss_pct=0.020,
    max_trades_per_day=12,
    max_consecutive_losses=3,
    allow_short=False,
    allow_averaging_down=False,
)

MTF_BB3_REVERSION_CONFIG = StrategyConfig(
    mode="multi_timeframe_bb3_reversion",
    stop_loss_pct=0.005,
    take_profit_pct=0.009,
    break_even_trigger_pct=0.006,
    trailing_start_pct=0.007,
    max_daily_loss_pct=0.020,
    max_trades_per_day=10,
    max_consecutive_losses=3,
    allow_short=True,
    allow_averaging_down=False,
)

ELEMENT_LOW_CONFIG = StrategyConfig(
    mode="element",
    stop_loss_pct=0.003,
    take_profit_pct=0.005,
    break_even_trigger_pct=0.004,
    trailing_start_pct=0.005,
    max_daily_loss_pct=0.005,
    max_trades_per_day=3,
    max_consecutive_losses=3,
    allow_short=False,
    allow_averaging_down=False,
)

ELEMENT_NORMAL_CONFIG = StrategyConfig(
    mode="element",
    stop_loss_pct=0.004,
    take_profit_pct=0.008,
    break_even_trigger_pct=0.005,
    trailing_start_pct=0.006,
    max_daily_loss_pct=0.010,
    max_trades_per_day=5,
    max_consecutive_losses=3,
    allow_short=False,
    allow_averaging_down=False,
)

ELEMENT_HIGH_CONFIG = StrategyConfig(
    mode="element",
    stop_loss_pct=0.005,
    take_profit_pct=0.010,
    break_even_trigger_pct=0.006,
    trailing_start_pct=0.006,
    max_daily_loss_pct=0.015,
    max_trades_per_day=8,
    max_consecutive_losses=3,
    allow_short=True,
    allow_averaging_down=False,
)


@dataclass
class StrategyContext:
    obs: dict
    minute: pd.DataFrame
    daily: pd.DataFrame
    timestamp: pd.Timestamp
    current: pd.Series
    previous: pd.Series | None

    @property
    def clock(self) -> time:
        return self.timestamp.time()

    @property
    def close(self) -> float:
        return _as_float(self.current.get("close"), self.obs.get("current_price", 0.0))

    @property
    def open(self) -> float:
        return _as_float(self.current.get("open"), self.close)

    @property
    def low(self) -> float:
        return _as_float(self.current.get("low"), self.close)

    @property
    def high(self) -> float:
        return _as_float(self.current.get("high"), self.close)

    @property
    def vwap(self) -> float | None:
        return _optional_float(self.current.get("vwap"))

    @property
    def ma_5(self) -> float | None:
        return _optional_float(self.current.get("ma_5"))

    @property
    def ma_25(self) -> float | None:
        return _optional_float(self.current.get("ma_25"))

    @property
    def bb_upper_2(self) -> float | None:
        return _optional_float(self.current.get("bb_upper_2"))

    @property
    def bb_lower_2(self) -> float | None:
        return _optional_float(self.current.get("bb_lower_2"))

    @property
    def bb_upper_3(self) -> float | None:
        return _optional_float(self.current.get("bb_upper_3"))

    @property
    def bb_lower_3(self) -> float | None:
        return _optional_float(self.current.get("bb_lower_3"))

    @property
    def volume_ratio(self) -> float:
        return _as_float(self.current.get("volume_ratio_5_to_25"), 0.0)

    @property
    def recent_5min_volume(self) -> float:
        return _as_float(self.current.get("recent_5min_volume"), 0.0)

    @property
    def avg_30min_volume(self) -> float:
        return _as_float(self.current.get("avg_30min_volume"), 0.0)

    @property
    def previous_day(self) -> pd.Series | None:
        if self.daily.empty:
            return None
        return self.daily.iloc[-1]


class DaytradeModeStrategy(Strategy):
    config = NORMAL_CONFIG
    direction = "long"
    risk_level = "normal"

    def decide(self, obs: dict) -> Action:
        ctx = _context(obs)
        position = obs["position"]
        if not position.is_flat:
            return Action.CLOSE if self._should_exit(ctx) else Action.HOLD
        if not self._can_enter(ctx):
            return Action.HOLD
        return self._entry_action(ctx)

    def _can_enter(self, ctx: StrategyContext) -> bool:
        obs = ctx.obs
        if not obs["position"].is_flat:
            return False
        if not _entry_time_allowed(ctx.clock, self.config):
            return False
        if self.config.max_trades_per_day is not None and _entry_count(obs) >= self.config.max_trades_per_day:
            return False
        if _consecutive_losses(obs) >= self.config.max_consecutive_losses:
            return False
        if _daily_loss_reached(obs, self.config):
            return False
        return True

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.HOLD

    def _should_exit(self, ctx: StrategyContext) -> bool:
        if _force_exit_time_reached(ctx.clock, self.config):
            return True
        if _daily_loss_reached(ctx.obs, self.config):
            return True
        if _fixed_stop_or_take_profit(ctx, self.config):
            return True
        if _break_even_exit(ctx, self.config):
            return True
        if _trailing_exit(ctx, self.config):
            return True
        if _bb3_overheat_take_profit(ctx):
            return True
        return self._mode_specific_exit(ctx)

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return False


class ElementVwapCrossStrategy(DaytradeModeStrategy):
    name = "element_vwap_cross"
    config = ELEMENT_LOW_CONFIG
    risk_level = "low"

    def _entry_action(self, ctx: StrategyContext) -> Action:
        previous = ctx.previous
        if previous is None or not _has_values(ctx, "vwap", "ma_5", "ma_25"):
            return Action.HOLD
        previous_close = _as_float(previous.get("close"), 0.0)
        previous_vwap = _as_float(previous.get("vwap"), 0.0)
        previous_day = ctx.previous_day
        previous_low = _as_float(previous_day.get("low"), 0.0) if previous_day is not None else 0.0
        if (
            previous_close <= previous_vwap
            and ctx.close > float(ctx.vwap)
            and ctx.close > float(ctx.ma_5)
            and float(ctx.ma_5) >= float(ctx.ma_25)
            and ctx.volume_ratio >= 1.0
            and (not previous_low or ctx.close >= previous_low)
        ):
            return Action.BUY
        return Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return ctx.vwap is not None and ctx.close < ctx.vwap


class ElementVwapPullbackStrategy(DaytradeModeStrategy):
    name = "element_vwap_pullback"
    config = ELEMENT_LOW_CONFIG
    risk_level = "low"

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.BUY if _vwap_pullback_entry(ctx) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return ctx.vwap is not None and ctx.close < ctx.vwap


class ElementMaCrossStrategy(DaytradeModeStrategy):
    name = "element_ma_cross"
    config = ELEMENT_NORMAL_CONFIG

    def _entry_action(self, ctx: StrategyContext) -> Action:
        previous = ctx.previous
        if previous is None or not _has_values(ctx, "vwap", "ma_5", "ma_25"):
            return Action.HOLD
        previous_ma_5 = _as_float(previous.get("ma_5"), 0.0)
        previous_ma_25 = _as_float(previous.get("ma_25"), 0.0)
        if (
            previous_ma_5 <= previous_ma_25
            and float(ctx.ma_5) > float(ctx.ma_25)
            and ctx.close > float(ctx.vwap)
            and ctx.close > float(ctx.ma_5)
            and ctx.volume_ratio >= 1.0
        ):
            return Action.BUY
        return Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        previous = ctx.previous
        if previous is None or not _has_values(ctx, "ma_5", "ma_25"):
            return False
        return _as_float(previous.get("ma_5"), 0.0) >= _as_float(previous.get("ma_25"), 0.0) and float(
            ctx.ma_5
        ) < float(ctx.ma_25)


class ElementRecentHighBreakoutStrategy(DaytradeModeStrategy):
    name = "element_recent_high_breakout"
    config = ELEMENT_NORMAL_CONFIG

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.BUY if _recent_high_breakout_entry(ctx, minutes=30, min_volume_ratio=1.2) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        position = ctx.obs["position"]
        entry_price = float(position.entry_price or ctx.close)
        return ctx.close < entry_price or (ctx.ma_5 is not None and ctx.close < ctx.ma_5)


class ElementPreviousDayHighBreakoutStrategy(DaytradeModeStrategy):
    name = "element_previous_day_high_breakout"
    config = ELEMENT_NORMAL_CONFIG

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.BUY if _previous_day_high_breakout_entry(ctx, min_volume_ratio=1.2) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        previous_day = ctx.previous_day
        if previous_day is None:
            return False
        previous_high = _as_float(previous_day.get("high"), 0.0)
        return ctx.close < previous_high or (ctx.ma_5 is not None and ctx.close < ctx.ma_5)


class ElementVolumeBreakoutStrategy(DaytradeModeStrategy):
    name = "element_volume_breakout"
    config = ELEMENT_HIGH_CONFIG
    risk_level = "high"

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.BUY if _volume_breakout_entry(ctx) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return (ctx.ma_5 is not None and ctx.close < ctx.ma_5) or (ctx.vwap is not None and ctx.close < ctx.vwap)


class ElementBb3ReversalShortStrategy(DaytradeModeStrategy):
    name = "element_bb3_reversal_short"
    config = ELEMENT_HIGH_CONFIG
    direction = "short"
    risk_level = "high"

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.SELL if _bb3_reversal_short_entry(ctx) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        if ctx.obs["position"].side != PositionSide.SHORT:
            return False
        return (ctx.bb_upper_2 is not None and ctx.close <= ctx.bb_upper_2) or (
            ctx.ma_5 is not None and ctx.close <= ctx.ma_5
        )


class ElementBb3TakeProfitStrategy(DaytradeModeStrategy):
    name = "element_bb3_take_profit"
    config = ELEMENT_LOW_CONFIG
    risk_level = "low"

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.BUY if _vwap_pullback_entry(ctx) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return _bb3_overheat_take_profit(ctx)


class CombinedLowRiskStrategy(DaytradeModeStrategy):
    name = "combined_low_risk"
    config = LOW_RISK_CONFIG
    risk_level = "low"

    def _can_enter(self, ctx: StrategyContext) -> bool:
        return super()._can_enter(ctx) and _daily_filter(ctx, "low")

    def _entry_action(self, ctx: StrategyContext) -> Action:
        return Action.BUY if _vwap_pullback_entry(ctx) else Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return (ctx.vwap is not None and ctx.close < ctx.vwap * 0.999) or ctx.close < _recent_low(ctx, 5)


class CombinedNormalStrategy(DaytradeModeStrategy):
    name = "combined_normal"
    config = NORMAL_CONFIG

    def _can_enter(self, ctx: StrategyContext) -> bool:
        return DaytradeModeStrategy._can_enter(self, ctx)

    def _entry_action(self, ctx: StrategyContext) -> Action:
        signal = _body_break_signal(ctx)
        if signal == "long":
            return Action.BUY
        if signal == "short" and self.config.allow_short:
            return Action.SELL
        return Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        position = ctx.obs["position"]
        signal = _body_break_signal(ctx)
        if position.side == PositionSide.LONG:
            return signal == "short"
        if position.side == PositionSide.SHORT:
            return signal == "long"
        return False


class CombinedHighRiskStrategy(DaytradeModeStrategy):
    name = "combined_high_risk"
    config = HIGH_RISK_CONFIG
    risk_level = "high"

    def _can_enter(self, ctx: StrategyContext) -> bool:
        return super()._can_enter(ctx) and _daily_filter(ctx, "high")

    def _entry_action(self, ctx: StrategyContext) -> Action:
        if _volume_breakout_entry(ctx):
            return Action.BUY
        if _previous_day_high_breakout_entry(ctx, min_volume_ratio=1.2):
            return Action.BUY
        if _bb2_momentum_entry(ctx):
            return Action.BUY
        if self.config.allow_short and _bb3_reversal_short_entry(ctx):
            return Action.SELL
        return Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        return (ctx.vwap is not None and ctx.close < ctx.vwap) or ctx.close < _recent_low(ctx, 5)


class MultiTimeframeBb3ReversionStrategy(DaytradeModeStrategy):
    name = "multi_timeframe_bb3_reversion"
    config = MTF_BB3_REVERSION_CONFIG
    direction = "both"
    risk_level = "normal"

    def _can_enter(self, ctx: StrategyContext) -> bool:
        return super()._can_enter(ctx) and len(ctx.minute) >= 20

    def _entry_action(self, ctx: StrategyContext) -> Action:
        signal = _multi_timeframe_bb3_signal(ctx)
        if signal == "long":
            return Action.BUY
        if signal == "short" and self.config.allow_short:
            return Action.SELL
        return Action.HOLD

    def _mode_specific_exit(self, ctx: StrategyContext) -> bool:
        position = ctx.obs["position"]
        signal = _multi_timeframe_bb3_signal(ctx, require_turn=False)
        if position.side == PositionSide.LONG:
            return signal == "short" or (ctx.vwap is not None and ctx.close >= ctx.vwap)
        if position.side == PositionSide.SHORT:
            return signal == "long" or (ctx.vwap is not None and ctx.close <= ctx.vwap)
        return False


DAYTRADE_MODE_STRATEGIES: dict[str, type[Strategy]] = {
    strategy.name: strategy
    for strategy in [
        ElementVwapCrossStrategy,
        ElementVwapPullbackStrategy,
        ElementMaCrossStrategy,
        ElementRecentHighBreakoutStrategy,
        ElementPreviousDayHighBreakoutStrategy,
        ElementVolumeBreakoutStrategy,
        ElementBb3ReversalShortStrategy,
        ElementBb3TakeProfitStrategy,
        CombinedLowRiskStrategy,
        CombinedNormalStrategy,
        CombinedHighRiskStrategy,
        MultiTimeframeBb3ReversionStrategy,
    ]
}

DAYTRADE_MODE_LABELS: dict[str, str] = {
    "combined_low_risk": "押し目重視手法",
    "combined_normal": "標準デイトレ手法",
    "combined_high_risk": "積極ブレイク手法",
    "multi_timeframe_bb3_reversion": "15/30/60分足 3σ逆張り",
}


def _context(obs: dict) -> StrategyContext:
    minute = obs["minute_bars"].copy()
    daily = obs["daily_bars"].copy()
    current = minute.iloc[-1]
    previous = minute.iloc[-2] if len(minute) >= 2 else None
    return StrategyContext(
        obs=obs,
        minute=minute,
        daily=daily,
        timestamp=pd.Timestamp(obs["timestamp"]),
        current=current,
        previous=previous,
    )


def _body_break_signal(ctx: StrategyContext, *, threshold_pct: float = 0.0005) -> str | None:
    if ctx.previous is None:
        return None

    current_body_low, current_body_high = _body_range(ctx.current)
    previous_body_low, previous_body_high = _body_range(ctx.previous)
    for column in ["vwap", "ma_5", "ma_25", "ma_75"]:
        current_line = _optional_float(ctx.current.get(column))
        previous_line = _optional_float(ctx.previous.get(column))
        if current_line is None or previous_line is None:
            continue
        upper_break_level = current_line * (1.0 + threshold_pct)
        previous_upper_level = previous_line * (1.0 + threshold_pct)
        if current_body_low > upper_break_level and previous_body_low <= previous_upper_level:
            return "long"

        lower_break_level = current_line * (1.0 - threshold_pct)
        previous_lower_level = previous_line * (1.0 - threshold_pct)
        if current_body_high < lower_break_level and previous_body_high >= previous_lower_level:
            return "short"
    return None


def _body_range(bar: pd.Series) -> tuple[float, float]:
    open_price = _as_float(bar.get("open"), _as_float(bar.get("close"), 0.0))
    close_price = _as_float(bar.get("close"), open_price)
    return min(open_price, close_price), max(open_price, close_price)


def _vwap_pullback_entry(ctx: StrategyContext) -> bool:
    if not _has_values(ctx, "vwap", "ma_5", "ma_25"):
        return False
    if not (ctx.close > float(ctx.vwap) and float(ctx.ma_5) >= float(ctx.ma_25) * 0.998):
        return False
    if not (_ma_rising(ctx, "ma_25") or ctx.close > float(ctx.ma_5)):
        return False
    if not (_recent_day_high_update(ctx, minutes=45) or ctx.close > _previous_high(ctx, 10)):
        return False
    pullback_level = max(float(ctx.vwap) * 1.006, float(ctx.ma_5) * 1.006)
    return ctx.low <= pullback_level and (ctx.close > _previous_high(ctx, 3) or ctx.close > float(ctx.ma_5)) and ctx.volume_ratio >= 0.7


def _recent_high_breakout_entry(ctx: StrategyContext, *, minutes: int, min_volume_ratio: float) -> bool:
    if not _has_values(ctx, "vwap", "ma_5", "ma_25"):
        return False
    return (
        ctx.close > _previous_high(ctx, minutes)
        and ctx.close > float(ctx.vwap)
        and float(ctx.ma_5) > float(ctx.ma_25)
        and ctx.volume_ratio >= min_volume_ratio
    )


def _previous_day_high_breakout_entry(ctx: StrategyContext, *, min_volume_ratio: float) -> bool:
    previous_day = ctx.previous_day
    if previous_day is None or not _has_values(ctx, "vwap", "ma_5", "ma_25"):
        return False
    return (
        ctx.close > _as_float(previous_day.get("high"), 0.0)
        and ctx.close > float(ctx.vwap)
        and float(ctx.ma_5) > float(ctx.ma_25)
        and ctx.volume_ratio >= min_volume_ratio
    )


def _volume_breakout_entry(ctx: StrategyContext) -> bool:
    if not _has_values(ctx, "vwap", "ma_5", "ma_25"):
        return False
    return (
        ctx.close > _previous_high(ctx, 15)
        and ctx.avg_30min_volume > 0
        and ctx.recent_5min_volume > ctx.avg_30min_volume * 1.25
        and ctx.close > float(ctx.vwap)
        and float(ctx.ma_5) > float(ctx.ma_25)
    )


def _bb2_momentum_entry(ctx: StrategyContext) -> bool:
    if not _has_values(ctx, "vwap", "ma_5", "ma_25", "bb_upper_2", "bb_upper_3"):
        return False
    return (
        ctx.close > float(ctx.bb_upper_2)
        and ctx.close < float(ctx.bb_upper_3)
        and float(ctx.ma_5) > float(ctx.ma_25)
        and ctx.close > float(ctx.vwap)
        and ctx.volume_ratio >= 1.3
    )


def _bb3_reversal_short_entry(ctx: StrategyContext) -> bool:
    if ctx.previous is None or not _has_values(ctx, "vwap", "bb_upper_3"):
        return False
    previous_close = _as_float(ctx.previous.get("close"), 0.0)
    return (
        ctx.close > float(ctx.bb_upper_3)
        and ctx.close < ctx.open
        and ctx.close < previous_close
        and ctx.volume_ratio < 1.2
        and ctx.close >= float(ctx.vwap) * 1.015
    )


def _multi_timeframe_bb3_signal(ctx: StrategyContext, require_turn: bool = True) -> str | None:
    if ctx.previous is None:
        return None
    previous_close = _as_float(ctx.previous.get("close"), ctx.close)
    turn_long = not require_turn or ctx.close > ctx.open or ctx.close > previous_close
    turn_short = not require_turn or ctx.close < ctx.open or ctx.close < previous_close

    for minutes in [15, 30, 60]:
        frame = _resampled_bollinger_frame(ctx.minute, minutes)
        if len(frame) < 3:
            continue
        latest = frame.iloc[-1]
        lower_3 = _optional_float(latest.get("bb_lower_3"))
        upper_3 = _optional_float(latest.get("bb_upper_3"))
        if lower_3 is None or upper_3 is None:
            continue
        stretched_lower = _as_float(latest.get("low"), ctx.low) < lower_3 or _as_float(latest.get("close"), ctx.close) < lower_3
        stretched_upper = _as_float(latest.get("high"), ctx.high) > upper_3 or _as_float(latest.get("close"), ctx.close) > upper_3
        if stretched_lower and turn_long:
            return "long"
        if stretched_upper and turn_short:
            return "short"
    return None


def _resampled_bollinger_frame(minute: pd.DataFrame, interval_minutes: int) -> pd.DataFrame:
    source = minute.copy().sort_values("timestamp")
    source["timestamp"] = pd.to_datetime(source["timestamp"])
    frame = (
        source.set_index("timestamp")
        .resample(f"{interval_minutes}min", origin="start_day")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna(subset=["open", "high", "low", "close"])
    )
    if frame.empty:
        return frame
    bands = bollinger_bands(frame["close"], 20)
    for column in bands.columns:
        frame[column] = bands[column]
    return frame.reset_index()


def _daily_filter(ctx: StrategyContext, level: str) -> bool:
    daily = ctx.daily
    if len(daily) < 2:
        return True
    previous_day = daily.iloc[-1]
    previous_close = _as_float(previous_day.get("close"), 0.0)
    daily_ma_25 = _as_float(previous_day.get("daily_ma_25"), 0.0)
    daily_ma_5 = _as_float(previous_day.get("daily_ma_5"), 0.0)
    avg_volume_20 = _as_float(previous_day.get("daily_volume_ma_20"), _as_float(daily["volume"].tail(20).mean(), 0.0))
    previous_volume = _as_float(previous_day.get("volume"), 0.0)
    current_open = _as_float(ctx.minute.iloc[0].get("open"), ctx.open)

    if previous_close <= 0 or avg_volume_20 <= 0:
        return False
    if level == "low":
        return (
            previous_close >= daily_ma_25 * 0.98
            and (daily_ma_5 >= daily_ma_25 * 0.98 or _daily_ma_rising(daily, "daily_ma_25"))
            and previous_volume >= avg_volume_20 * 0.5
            and current_open >= previous_close * 0.96
            and current_open <= previous_close * 1.08
        )
    if level == "normal":
        return (
            previous_close >= daily_ma_25 * 0.95
            and current_open >= previous_close * 0.95
            and current_open <= previous_close * 1.15
            and previous_volume >= avg_volume_20 * 0.4
        )
    return current_open >= previous_close * 0.92 and current_open <= previous_close * 1.18 and previous_volume >= avg_volume_20 * 0.3


def _fixed_stop_or_take_profit(ctx: StrategyContext, config: StrategyConfig) -> bool:
    pnl_rate = _position_pnl_rate(ctx)
    return pnl_rate <= -config.stop_loss_pct or pnl_rate >= config.take_profit_pct


def _break_even_exit(ctx: StrategyContext, config: StrategyConfig) -> bool:
    position = ctx.obs["position"]
    entry_price = float(position.entry_price or 0.0)
    if entry_price <= 0:
        return False
    if _max_favorable_move(ctx) < config.break_even_trigger_pct:
        return False
    if position.side == PositionSide.LONG:
        return ctx.close <= entry_price
    return ctx.close >= entry_price


def _trailing_exit(ctx: StrategyContext, config: StrategyConfig) -> bool:
    if _max_favorable_move(ctx) < config.trailing_start_pct:
        return False
    position = ctx.obs["position"]
    if position.side == PositionSide.LONG:
        return (
            (ctx.ma_5 is not None and ctx.close < ctx.ma_5)
            or ctx.close < _recent_low(ctx, 5)
            or (ctx.vwap is not None and ctx.close < ctx.vwap)
        )
    return (
        (ctx.ma_5 is not None and ctx.close > ctx.ma_5)
        or ctx.close > _recent_high(ctx, 5)
        or (ctx.vwap is not None and ctx.close > ctx.vwap)
    )


def _bb3_overheat_take_profit(ctx: StrategyContext) -> bool:
    position = ctx.obs["position"]
    if position.side != PositionSide.LONG or not _has_overheat_since_entry(ctx):
        return False
    return ctx.close < ctx.open or (ctx.previous is not None and ctx.close < _as_float(ctx.previous.get("low"), 0.0)) or (
        ctx.ma_5 is not None and ctx.close < ctx.ma_5
    )


def _has_overheat_since_entry(ctx: StrategyContext) -> bool:
    position = ctx.obs["position"]
    if position.entry_time is None or "bb_upper_3" not in ctx.minute:
        return False
    since_entry = _minute_since_entry(ctx)
    if since_entry.empty:
        return False
    return bool((since_entry["close"].astype(float) > since_entry["bb_upper_3"].astype(float)).any())


def _max_favorable_move(ctx: StrategyContext) -> float:
    position = ctx.obs["position"]
    entry_price = float(position.entry_price or 0.0)
    if entry_price <= 0:
        return 0.0
    since_entry = _minute_since_entry(ctx)
    if since_entry.empty:
        return 0.0
    if position.side == PositionSide.LONG:
        return (float(since_entry["high"].max()) - entry_price) / entry_price
    return (entry_price - float(since_entry["low"].min())) / entry_price


def _position_pnl_rate(ctx: StrategyContext) -> float:
    position = ctx.obs["position"]
    entry_price = float(position.entry_price or 0.0)
    if entry_price <= 0:
        return 0.0
    if position.side == PositionSide.LONG:
        return (ctx.close - entry_price) / entry_price
    return (entry_price - ctx.close) / entry_price


def _minute_since_entry(ctx: StrategyContext) -> pd.DataFrame:
    entry_time = ctx.obs["position"].entry_time
    if entry_time is None:
        return ctx.minute.tail(0)
    timestamps = pd.to_datetime(ctx.minute["timestamp"])
    return ctx.minute[timestamps >= pd.Timestamp(entry_time)]


def _entry_time_allowed(clock: time, config: StrategyConfig) -> bool:
    if clock < _parse_time(config.entry_start_time) or clock >= _parse_time(config.entry_end_time):
        return False
    if time(11, 25) <= clock < time(12, 35):
        return False
    return True


def _force_exit_time_reached(clock: time, config: StrategyConfig) -> bool:
    return clock >= _parse_time(config.force_exit_time)


def _entry_count(obs: dict) -> int:
    return sum(1 for fill in obs.get("fills", []) if fill.get("action") == "OPEN")


def _consecutive_losses(obs: dict) -> int:
    losses = 0
    for trade in reversed(obs.get("trades", [])):
        pnl = _as_float(getattr(trade, "pnl", None) if not isinstance(trade, dict) else trade.get("pnl"), 0.0)
        if pnl < 0:
            losses += 1
            continue
        break
    return losses


def _daily_loss_reached(obs: dict, config: StrategyConfig) -> bool:
    initial_cash = _as_float(obs.get("initial_cash"), DEFAULT_INITIAL_CASH)
    total_pnl = _as_float(obs.get("realized_pnl"), 0.0) + _as_float(obs.get("unrealized_pnl"), 0.0)
    return total_pnl <= -(initial_cash * config.max_daily_loss_pct)


def _has_values(ctx: StrategyContext, *columns: str) -> bool:
    return all(_optional_float(ctx.current.get(column)) is not None for column in columns)


def _ma_rising(ctx: StrategyContext, column: str, lookback: int = 5) -> bool:
    if column not in ctx.minute or len(ctx.minute) <= lookback:
        return False
    current = _optional_float(ctx.minute[column].iloc[-1])
    previous = _optional_float(ctx.minute[column].iloc[-lookback - 1])
    return current is not None and previous is not None and current > previous


def _daily_ma_rising(daily: pd.DataFrame, column: str) -> bool:
    if column not in daily or len(daily) < 2:
        return False
    current = _optional_float(daily[column].iloc[-1])
    previous = _optional_float(daily[column].iloc[-2])
    return current is not None and previous is not None and current > previous


def _recent_day_high_update(ctx: StrategyContext, minutes: int) -> bool:
    if ctx.minute.empty:
        return False
    recent = ctx.minute.tail(minutes)
    return float(recent["high"].max()) >= float(ctx.minute["high"].max())


def _previous_high(ctx: StrategyContext, minutes: int) -> float:
    if len(ctx.minute) <= 1:
        return float("inf")
    return float(ctx.minute.iloc[:-1]["high"].tail(minutes).max())


def _recent_high(ctx: StrategyContext, minutes: int) -> float:
    return float(ctx.minute["high"].tail(minutes).max())


def _recent_low(ctx: StrategyContext, minutes: int) -> float:
    return float(ctx.minute["low"].tail(minutes).min())


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _as_float(value: object, default: float) -> float:
    number = _optional_float(value)
    return default if number is None else number
