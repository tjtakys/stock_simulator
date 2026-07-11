from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from mobile_api.schemas import (
    CreateReplaySessionRequest,
    DailyBarResponse,
    HealthResponse,
    ReplayCommandRequest,
    ReplayStateResponse,
)
from mobile_api.service import ReplaySessionService, SessionNotFound
from mobile_api.session_store import session_store
from src.data.loader import DataSource


app = FastAPI(title="Stock Simulator Mobile API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
service = ReplaySessionService(session_store)


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/v1/market-data/daily", response_model=list[DailyBarResponse])
def daily_market_data(
    symbol: str = Query(min_length=1, max_length=12),
    trading_date: date = Query(),
    data_source: DataSource = Query(default="sample"),
) -> list[DailyBarResponse]:
    try:
        return service.daily_bars(symbol, trading_date, data_source)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.post("/api/v1/replay-sessions", response_model=ReplayStateResponse, status_code=status.HTTP_201_CREATED)
def create_replay_session(request: CreateReplaySessionRequest) -> ReplayStateResponse:
    try:
        return service.create(request)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.get("/api/v1/replay-sessions/{session_id}", response_model=ReplayStateResponse)
def get_replay_session(session_id: str) -> ReplayStateResponse:
    try:
        return service.get(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="練習セッションが見つかりません。") from exc


@app.post("/api/v1/replay-sessions/{session_id}/commands", response_model=ReplayStateResponse)
def execute_replay_command(session_id: str, request: ReplayCommandRequest) -> ReplayStateResponse:
    try:
        return service.command(session_id, request)
    except SessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="練習セッションが見つかりません。") from exc


@app.get("/api/v1/replay-sessions/{session_id}/result", response_model=ReplayStateResponse)
def get_replay_result(session_id: str) -> ReplayStateResponse:
    return get_replay_session(session_id)


@app.delete("/api/v1/replay-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_replay_session(session_id: str) -> None:
    try:
        service.delete(session_id)
    except SessionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="練習セッションが見つかりません。") from exc
