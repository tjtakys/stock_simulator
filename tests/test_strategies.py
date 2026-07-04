from datetime import datetime

import pandas as pd

from src.simulator.position import Position, PositionSide
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
