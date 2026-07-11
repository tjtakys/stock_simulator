from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.data.loader import DataSource


class CommandType(str, Enum):
    STEP_FORWARD = "STEP_FORWARD"
    STEP_BACK = "STEP_BACK"
    RESET = "RESET"
    BUY = "BUY"
    SELL_SHORT = "SELL_SHORT"
    CLOSE = "CLOSE"
    FINISH = "FINISH"


class HealthResponse(BaseModel):
    status: str = "ok"
    api_version: str = "1"


class CreateReplaySessionRequest(BaseModel):
    symbol: str = Field(default="285A", min_length=1, max_length=12)
    trading_date: date = date(2026, 6, 24)
    data_source: DataSource = "sample"
    initial_cash: float = Field(default=10_000_000, gt=0)
    order_quantity: int = Field(default=100, gt=0)


class ReplayCommandRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=100)
    command: CommandType


class BarResponse(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    ma_5: float | None = None
    ma_25: float | None = None
    ma_75: float | None = None
    bb_middle: float | None = None
    bb_upper_1: float | None = None
    bb_lower_1: float | None = None
    bb_upper_2: float | None = None
    bb_lower_2: float | None = None
    bb_upper_3: float | None = None
    bb_lower_3: float | None = None


class PositionResponse(BaseModel):
    side: str
    quantity: int
    entry_price: float | None = None
    entry_time: datetime | None = None


class FillResponse(BaseModel):
    timestamp: datetime
    symbol: str
    action: str
    side: str
    quantity: int
    price: float
    pnl: float | None = None


class TradeResponse(BaseModel):
    symbol: str
    entry_time: datetime
    exit_time: datetime
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float


class ReplayStateResponse(BaseModel):
    session_id: str
    revision: int
    symbol: str
    trading_date: date
    timestamp: datetime
    current_price: float
    minute_bars: list[BarResponse]
    position: PositionResponse
    fills: list[FillResponse]
    trades: list[TradeResponse]
    realized_pnl: float
    unrealized_pnl: float
    equity: float
    initial_cash: float
    available_cash: float
    committed_notional: float
    done: bool
    last_message: str | None = None


class DailyBarResponse(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
