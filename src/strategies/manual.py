from src.simulator.order import Action
from src.strategies.base import Strategy


class ManualStrategy(Strategy):
    name = "manual"

    def __init__(self, action: Action = Action.HOLD) -> None:
        self.action = action

    def decide(self, obs: dict) -> Action:
        del obs
        return self.action
