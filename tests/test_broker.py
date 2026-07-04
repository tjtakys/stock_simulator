from datetime import datetime

from src.simulator.broker import SimulatedBroker
from src.simulator.order import Action
from src.simulator.position import PositionSide


def test_broker_opens_and_closes_long_position():
    broker = SimulatedBroker("285A")
    now = datetime(2026, 6, 24, 9, 0)

    broker.execute_action(Action.BUY, price=100.0, timestamp=now, quantity=10)
    assert broker.position.side == PositionSide.LONG

    broker.execute_action(Action.SELL, price=110.0, timestamp=now, quantity=10)

    assert broker.position.side == PositionSide.FLAT
    assert broker.realized_pnl == 100.0
    assert len(broker.trades) == 1


def test_broker_calculates_short_unrealized_pnl():
    broker = SimulatedBroker("285A")
    now = datetime(2026, 6, 24, 9, 0)

    broker.execute_action(Action.SELL, price=100.0, timestamp=now, quantity=10)

    assert broker.unrealized_pnl(90.0) == 100.0


def test_broker_allows_adding_same_side_within_cash_limit():
    broker = SimulatedBroker("285A", initial_cash=10_000.0)
    now = datetime(2026, 6, 24, 9, 0)

    broker.execute_action(Action.BUY, price=100.0, timestamp=now, quantity=10)
    result = broker.execute_action(Action.BUY, price=200.0, timestamp=now, quantity=10)

    assert result["status"] == "filled"
    assert broker.position.quantity == 20
    assert broker.position.entry_price == 150.0
    assert broker.available_cash() == 7_000.0


def test_broker_rejects_order_over_cash_limit():
    broker = SimulatedBroker("285A", initial_cash=1_000.0)
    now = datetime(2026, 6, 24, 9, 0)

    result = broker.execute_action(Action.BUY, price=100.0, timestamp=now, quantity=11)

    assert result["status"] == "rejected"
    assert broker.position.is_flat
