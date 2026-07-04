from __future__ import annotations

from abc import ABC, abstractmethod

from src.simulator.order import Action


class Strategy(ABC):
    name = "base"

    @abstractmethod
    def decide(self, obs: dict) -> Action:
        raise NotImplementedError


def get_strategy(name: str) -> Strategy:
    from src.strategies.bollinger_reversion import BollingerReversionStrategy
    from src.strategies.combined_rule import CombinedRuleStrategy
    from src.strategies.vwap_ma_breakout import VwapMaBreakoutStrategy

    strategies: dict[str, type[Strategy]] = {
        VwapMaBreakoutStrategy.name: VwapMaBreakoutStrategy,
        BollingerReversionStrategy.name: BollingerReversionStrategy,
        CombinedRuleStrategy.name: CombinedRuleStrategy,
    }
    try:
        return strategies[name]()
    except KeyError as exc:
        choices = ", ".join(sorted(strategies))
        raise ValueError(f"未対応の戦略です: {name}。選択可能: {choices}") from exc
