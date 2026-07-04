from dataclasses import dataclass

from src.simulator.order import Action
from src.simulator.position import PositionSide


@dataclass
class RiskManager:
    max_quantity: int = 10_000
    max_daily_loss: float = 50_000.0
    stop_loss: float = 20_000.0

    def approve(self, action: Action, obs: dict, quantity: int) -> tuple[Action, str]:
        if quantity > self.max_quantity and action in {Action.BUY, Action.SELL}:
            return Action.HOLD, "quantity limit"

        if obs["realized_pnl"] <= -self.max_daily_loss:
            if obs["position"].side != PositionSide.FLAT:
                return Action.CLOSE, "daily loss limit"
            return Action.HOLD, "daily loss limit"

        if obs["unrealized_pnl"] <= -self.stop_loss and obs["position"].side != PositionSide.FLAT:
            return Action.CLOSE, "stop loss"

        return action, "approved"
