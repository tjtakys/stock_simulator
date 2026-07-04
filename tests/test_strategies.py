from datetime import datetime

import pandas as pd

from src.simulator.position import Position, PositionSide
from src.strategies.base import get_strategy
from src.strategies.bollinger_next_reversion import BollingerNextBarReversionStrategy
from src.strategies.bollinger_reversion import BollingerReversionStrategy
from src.strategies.vwap_ma_breakout import VwapMaBreakoutStrategy
from src.simulator.order import Action


def _obs(position=None, **indicators):
    return {
        "current_price": 110.0,
        "timestamp": datetime(2026, 6, 24, 9, 0),
        "minute_bars": pd.DataFrame({"high": [100.0, 105.0, 109.0], "close": [100.0, 105.0, 110.0]}),
        "daily_bars": pd.DataFrame({"close": [100.0]}),
        "indicators": indicators,
        "position": position or Position(),
    }


def test_vwap_ma_breakout_buys_when_conditions_align():
    strategy = VwapMaBreakoutStrategy()
    obs = _obs(vwap=100.0, ma_5=108.0, ma_25=104.0)

    assert strategy.decide(obs) == Action.BUY


def test_vwap_ma_breakout_closes_long_below_vwap():
    strategy = VwapMaBreakoutStrategy()
    position = Position(side=PositionSide.LONG, quantity=1, entry_price=120.0, entry_time=datetime(2026, 6, 24, 9, 0))
    obs = _obs(position=position, vwap=120.0, ma_5=111.0, ma_25=100.0)

    assert strategy.decide(obs) == Action.CLOSE


def test_bollinger_reversion_buys_below_lower_band():
    strategy = BollingerReversionStrategy()
    obs = _obs(bb_middle=120.0, bb_upper_3=140.0, bb_lower_3=115.0)

    assert strategy.decide(obs) == Action.BUY


def _bollinger_next_obs(position=None, current_price=100.0, previous_close=90.0, current_close=100.0):
    minute = pd.DataFrame(
        {
            "close": [100.0] * 19 + [previous_close, current_close],
            "high": [101.0] * 21,
            "low": [99.0] * 21,
            "bb_upper_3": [120.0] * 21,
            "bb_lower_3": [95.0] * 21,
        }
    )
    return {
        "current_price": current_price,
        "timestamp": datetime(2026, 6, 24, 9, 21),
        "minute_bars": minute,
        "daily_bars": pd.DataFrame({"close": [100.0]}),
        "indicators": {},
        "position": position or Position(),
    }


def test_bollinger_next_reversion_waits_until_next_bar_to_enter():
    strategy = BollingerNextBarReversionStrategy()
    obs = _bollinger_next_obs(previous_close=100.0, current_close=90.0)

    assert strategy.decide(obs) == Action.HOLD


def test_bollinger_next_reversion_buys_after_previous_lower_break():
    strategy = BollingerNextBarReversionStrategy()
    obs = _bollinger_next_obs(previous_close=90.0)

    assert strategy.decide(obs) == Action.BUY


def test_bollinger_next_reversion_sells_after_previous_upper_break():
    strategy = BollingerNextBarReversionStrategy()
    obs = _bollinger_next_obs(previous_close=130.0)

    assert strategy.decide(obs) == Action.SELL


def test_bollinger_next_reversion_takes_profit_when_position_is_profitable():
    strategy = BollingerNextBarReversionStrategy()
    position = Position(side=PositionSide.LONG, quantity=1, entry_price=100.0, entry_time=datetime(2026, 6, 24, 9, 0))
    obs = _bollinger_next_obs(position=position, current_price=101.0)

    assert strategy.decide(obs) == Action.CLOSE


def test_bollinger_next_reversion_cuts_loss_at_five_percent():
    strategy = BollingerNextBarReversionStrategy()
    position = Position(side=PositionSide.LONG, quantity=1, entry_price=100.0, entry_time=datetime(2026, 6, 24, 9, 0))
    obs = _bollinger_next_obs(position=position, current_price=95.0)

    assert strategy.decide(obs) == Action.CLOSE


def test_get_strategy_returns_bollinger_next_reversion():
    assert isinstance(get_strategy("bollinger_next_reversion"), BollingerNextBarReversionStrategy)
