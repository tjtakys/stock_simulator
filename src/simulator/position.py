from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class Position(BaseModel):
    side: PositionSide = PositionSide.FLAT
    quantity: int = Field(default=0, ge=0)
    entry_price: float | None = None
    entry_time: datetime | None = None

    @property
    def is_flat(self) -> bool:
        return self.side == PositionSide.FLAT or self.quantity == 0
