from src.simulator.order import Action
from src.simulator.position import PositionSide
from src.strategies.base import Strategy


class BollingerReversionStrategy(Strategy):
    name = "bollinger_reversion"

    def decide(self, obs: dict) -> Action:
        price = obs["current_price"]
        indicators = obs["indicators"]
        position = obs["position"]
        middle = indicators.get("bb_middle")
        upper_3 = indicators.get("bb_upper_3")
        lower_3 = indicators.get("bb_lower_3")

        if middle is None or upper_3 is None or lower_3 is None:
            return Action.HOLD

        if position.side == PositionSide.FLAT:
            if price < lower_3:
                return Action.BUY
            if price > upper_3:
                return Action.SELL
            return Action.HOLD

        if position.side == PositionSide.LONG and price >= middle:
            return Action.CLOSE
        if position.side == PositionSide.SHORT and price <= middle:
            return Action.CLOSE
        return Action.HOLD
