from datetime import date

import pandas as pd

from src.simulator.environment import TradingEnvironment
from src.simulator.order import Action


def _minute_bars():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-24 09:00:00", "2026-06-24 09:01:00"]),
            "open": [100.0, 100.0],
            "high": [101.0, 112.0],
            "low": [99.0, 99.0],
            "close": [100.0, 110.0],
            "volume": [1000, 1500],
        }
    )


def _daily_bars():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-22", "2026-06-23", "2026-06-24"]),
            "open": [90.0, 95.0, 100.0],
            "high": [100.0, 105.0, 112.0],
            "low": [85.0, 90.0, 99.0],
            "close": [95.0, 100.0, 110.0],
            "volume": [1000, 1000, 2500],
        }
    )


def test_environment_step_executes_action_and_tracks_pnl():
    env = TradingEnvironment("285A", date(2026, 6, 24), _minute_bars(), _daily_bars(), order_quantity=1)
    obs = env.reset()

    assert len(obs["minute_bars"]) == 1

    obs, _, done, _ = env.step(Action.BUY, quantity=1)
    assert not done

    obs, _, done, _ = env.step(Action.CLOSE, quantity=1)

    assert done
    assert obs["realized_pnl"] == 10.0


def test_environment_observation_does_not_expose_future_minute_bars():
    env = TradingEnvironment("285A", date(2026, 6, 24), _minute_bars(), _daily_bars(), order_quantity=1)
    obs = env.reset()

    assert len(obs["minute_bars"]) == 1
    assert obs["daily_bars"]["date"].dt.date.max() == date(2026, 6, 23)
    assert obs["daily_bars"].iloc[-1]["high"] == 105.0
    assert obs["daily_bars"].iloc[-1]["close"] == 100.0


def test_environment_does_not_substitute_current_day_when_no_prior_daily_bars():
    daily = _daily_bars()[_daily_bars()["date"].dt.date >= date(2026, 6, 24)]
    env = TradingEnvironment("285A", date(2026, 6, 24), _minute_bars(), daily, order_quantity=1)
    obs = env.reset()

    assert obs["daily_bars"].empty
    assert obs["indicators"]["daily_ma_5"] is None
