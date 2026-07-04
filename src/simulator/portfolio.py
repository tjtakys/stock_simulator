from pydantic import BaseModel


class PortfolioSnapshot(BaseModel):
    realized_pnl: float
    unrealized_pnl: float
    equity: float
