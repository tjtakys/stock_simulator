from fastapi.testclient import TestClient

from mobile_api.main import app
from mobile_api.session_store import session_store


client = TestClient(app)


def setup_function() -> None:
    session_store.clear()


def create_session() -> dict:
    response = client.post(
        "/api/v1/replay-sessions",
        json={
            "symbol": "285A",
            "trading_date": "2026-06-24",
            "data_source": "sample",
            "initial_cash": 10_000_000,
            "order_quantity": 100,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "api_version": "1"}


def test_session_never_exposes_future_minute_bars() -> None:
    state = create_session()
    assert len(state["minute_bars"]) == 1
    first_timestamp = state["minute_bars"][0]["timestamp"]

    response = client.post(
        f"/api/v1/replay-sessions/{state['session_id']}/commands",
        json={"command_id": "step-1", "command": "STEP_FORWARD"},
    )
    assert response.status_code == 200
    advanced = response.json()
    assert len(advanced["minute_bars"]) == 2
    assert advanced["minute_bars"][0]["timestamp"] == first_timestamp


def test_duplicate_command_id_does_not_double_fill() -> None:
    state = create_session()
    command = {"command_id": "buy-once", "command": "BUY"}
    first = client.post(f"/api/v1/replay-sessions/{state['session_id']}/commands", json=command)
    second = client.post(f"/api/v1/replay-sessions/{state['session_id']}/commands", json=command)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(second.json()["fills"]) == 1
    assert second.json()["position"]["quantity"] == 100


def test_buy_close_and_result() -> None:
    state = create_session()
    session_id = state["session_id"]
    bought = client.post(
        f"/api/v1/replay-sessions/{session_id}/commands",
        json={"command_id": "buy", "command": "BUY"},
    ).json()
    assert bought["position"]["side"] == "LONG"

    closed = client.post(
        f"/api/v1/replay-sessions/{session_id}/commands",
        json={"command_id": "close", "command": "CLOSE"},
    ).json()
    assert closed["position"]["side"] == "FLAT"
    assert len(closed["trades"]) == 1
    assert closed["revision"] == 2


def test_daily_market_data_excludes_trading_date() -> None:
    response = client.get(
        "/api/v1/market-data/daily",
        params={"symbol": "285A", "trading_date": "2026-06-24", "data_source": "sample"},
    )
    assert response.status_code == 200
    assert response.json()
    assert max(row["date"] for row in response.json()) < "2026-06-24"


def test_missing_session_returns_japanese_404() -> None:
    response = client.get("/api/v1/replay-sessions/not-found")
    assert response.status_code == 404
    assert response.json()["detail"] == "練習セッションが見つかりません。"
