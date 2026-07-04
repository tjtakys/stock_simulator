from src.simulator.order import Action
from src.simulator.position import PositionSide
from src.strategies.base import Strategy


class VwapMaBreakoutStrategy(Strategy):
    name = "vwap_ma_breakout"

    def decide(self, obs: dict) -> Action:
        price = obs["current_price"]
        indicators = obs["indicators"]
        position = obs["position"]
        vwap = indicators.get("vwap")
        ma_5 = indicators.get("ma_5")
        ma_25 = indicators.get("ma_25")

        if vwap is None or ma_5 is None or ma_25 is None:
            return Action.HOLD

        if position.side == PositionSide.FLAT:
            if price > vwap and price > ma_5 and ma_5 > ma_25:
                return Action.BUY
            return Action.HOLD

        if position.side == PositionSide.LONG and (price < vwap or price < ma_25):
            return Action.CLOSE

        return Action.HOLD
