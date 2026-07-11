from __future__ import annotations

from datetime import date
from math import isnan
from uuid import uuid4

import pandas as pd

from mobile_api.schemas import (
    BarResponse,
    CommandType,
    CreateReplaySessionRequest,
    DailyBarResponse,
    FillResponse,
    PositionResponse,
    ReplayCommandRequest,
    ReplayStateResponse,
    TradeResponse,
)
from mobile_api.session_store import InMemorySessionStore, ReplaySession
from src.data.loader import DataSource, load_daily_bars
from src.simulator.environment import TradingEnvironment
from src.simulator.order import Action


class SessionNotFound(KeyError):
    pass


class ReplaySessionService:
    def __init__(self, store: InMemorySessionStore) -> None:
        self.store = store

    def create(self, request: CreateReplaySessionRequest) -> ReplayStateResponse:
        environment = TradingEnvironment(
            request.symbol.strip().upper(),
            request.trading_date,
            initial_cash=request.initial_cash,
            order_quantity=request.order_quantity,
            data_source=request.data_source,
        )
        environment.reset()
        session_id = str(uuid4())
        session = ReplaySession(environment=environment)
        self.store.put(session_id, session)
        return self._state(session_id, session, "練習を開始しました。")

    def get(self, session_id: str) -> ReplayStateResponse:
        session = self._require(session_id)
        return self._state(session_id, session)

    def command(self, session_id: str, request: ReplayCommandRequest) -> ReplayStateResponse:
        with self.store.lock:
            session = self._require(session_id)
            cached = session.command_results.get(request.command_id)
            if cached is not None:
                return cached

            message = self._apply(session, request.command)
            session.revision += 1
            result = self._state(session_id, session, message)
            session.command_results[request.command_id] = result
            return result

    def delete(self, session_id: str) -> None:
        if not self.store.delete(session_id):
            raise SessionNotFound(session_id)

    def daily_bars(self, symbol: str, trading_date: date, data_source: DataSource) -> list[DailyBarResponse]:
        frame = load_daily_bars(symbol.strip().upper(), trading_date, data_source=data_source)
        frame = frame[pd.to_datetime(frame["date"]).dt.date < trading_date]
        return [
            DailyBarResponse(
                date=pd.Timestamp(row.date).date(),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=int(row.volume),
            )
            for row in frame.itertuples(index=False)
        ]

    def _require(self, session_id: str) -> ReplaySession:
        session = self.store.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        return session

    def _apply(self, session: ReplaySession, command: CommandType) -> str:
        environment = session.environment
        if command == CommandType.STEP_BACK:
            environment.retreat()
            return "1分戻りました。"
        if command == CommandType.RESET:
            environment.reset()
            return "練習を最初に戻しました。"
        if command == CommandType.FINISH:
            if not environment.broker.position.is_flat:
                state = environment.engine.current_state()
                fill = environment.broker.execute_action(
                    Action.CLOSE,
                    price=state["current_price"],
                    timestamp=state["timestamp"],
                    quantity=environment.order_quantity,
                )
                environment.done = True
                return self._fill_message(fill, "練習を終了しました。")
            environment.done = True
            return "練習を終了しました。"

        action = {
            CommandType.STEP_FORWARD: Action.HOLD,
            CommandType.BUY: Action.BUY,
            CommandType.SELL_SHORT: Action.SELL,
            CommandType.CLOSE: Action.CLOSE,
        }[command]
        _, _, _, info = environment.step(action)
        return self._fill_message(info.get("fill"), "1分進みました。" if action == Action.HOLD else None)

    @staticmethod
    def _fill_message(fill_info: dict | None, fallback: str | None = None) -> str:
        if not fill_info:
            return fallback or "操作を完了しました。"
        status = fill_info.get("status")
        if status in {"rejected", "ignored"}:
            return str(fill_info.get("reason") or "注文を実行できませんでした。")
        fill = fill_info.get("fill")
        if status == "filled" and fill:
            action = "決済" if fill["action"] == "CLOSE" else ("買い" if fill["side"] == "LONG" else "空売り")
            return f"{action} {int(fill['quantity']):,}株を {float(fill['price']):,.0f}円で約定しました。"
        return fallback or "操作を完了しました。"

    def _state(self, session_id: str, session: ReplaySession, message: str | None = None) -> ReplayStateResponse:
        obs = session.environment._observation()
        return ReplayStateResponse(
            session_id=session_id,
            revision=session.revision,
            symbol=obs["symbol"],
            trading_date=obs["date"],
            timestamp=pd.Timestamp(obs["timestamp"]).to_pydatetime(),
            current_price=float(obs["current_price"]),
            minute_bars=[self._bar(row) for row in obs["minute_bars"].to_dict("records")],
            position=PositionResponse(
                side=obs["position"].side.value,
                quantity=obs["position"].quantity,
                entry_price=obs["position"].entry_price,
                entry_time=obs["position"].entry_time,
            ),
            fills=[
                FillResponse(
                    timestamp=pd.Timestamp(fill["timestamp"]).to_pydatetime(),
                    symbol=fill["symbol"],
                    action=fill["action"],
                    side=fill["side"],
                    quantity=int(fill["quantity"]),
                    price=float(fill["price"]),
                    pnl=float(fill["pnl"]) if fill.get("pnl") is not None else None,
                )
                for fill in obs["fills"]
            ],
            trades=[
                TradeResponse(
                    symbol=trade.symbol,
                    entry_time=trade.entry_time,
                    exit_time=trade.exit_time,
                    side=trade.side.value,
                    quantity=trade.quantity,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    pnl=trade.pnl,
                )
                for trade in obs["trades"]
            ],
            realized_pnl=float(obs["realized_pnl"]),
            unrealized_pnl=float(obs["unrealized_pnl"]),
            equity=float(obs["equity"]),
            initial_cash=float(obs["initial_cash"]),
            available_cash=float(obs["available_cash"]),
            committed_notional=float(obs["committed_notional"]),
            done=bool(obs["done"]),
            last_message=message,
        )

    @staticmethod
    def _bar(row: dict) -> BarResponse:
        def optional(name: str) -> float | None:
            value = row.get(name)
            if value is None or pd.isna(value) or (isinstance(value, float) and isnan(value)):
                return None
            return float(value)

        return BarResponse(
            timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
            **{name: optional(name) for name in BarResponse.model_fields if name not in {"timestamp", "open", "high", "low", "close", "volume"}},
        )
