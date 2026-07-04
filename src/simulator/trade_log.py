from datetime import datetime

from pydantic import BaseModel

from src.simulator.position import PositionSide


class Trade(BaseModel):
    symbol: str
    entry_time: datetime
    exit_time: datetime
    side: PositionSide
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
