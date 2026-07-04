from src.simulator.order import Action
from src.simulator.position import PositionSide
from src.strategies.base import Strategy


class CombinedRuleStrategy(Strategy):
    name = "combined_rule"

    def decide(self, obs: dict) -> Action:
        price = obs["current_price"]
        indicators = obs["indicators"]
        position = obs["position"]
        minute = obs["minute_bars"]
        daily = obs["daily_bars"]

        if len(minute) < 25 or len(daily) < 75:
            return Action.HOLD

        vwap = indicators.get("vwap")
        ma_5 = indicators.get("ma_5")
        ma_25 = indicators.get("ma_25")
        daily_ma_25 = indicators.get("daily_ma_25")
        daily_ma_75 = indicators.get("daily_ma_75")
        if None in [vwap, ma_5, ma_25, daily_ma_25, daily_ma_75]:
            return Action.HOLD

        previous_daily = daily.iloc[-2] if len(daily) >= 2 else None
        recent_high = float(minute["high"].iloc[-20:-1].max())
        daily_uptrend = price > daily_ma_25 and daily_ma_25 > daily_ma_75
        breakout = price > recent_high
        previous_high_break = previous_daily is not None and price > float(previous_daily["high"])

        if position.side == PositionSide.FLAT:
            if daily_uptrend and previous_high_break and price > vwap and ma_5 > ma_25 and breakout:
                return Action.BUY
            return Action.HOLD

        if position.side == PositionSide.LONG and (price < vwap or ma_5 < ma_25):
            return Action.CLOSE
        return Action.HOLD
