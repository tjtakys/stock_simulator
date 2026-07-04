from datetime import date, datetime

from pydantic import BaseModel, Field


class MinuteBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = Field(ge=0)


class DailyBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int = Field(ge=0)


MINUTE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
DAILY_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
