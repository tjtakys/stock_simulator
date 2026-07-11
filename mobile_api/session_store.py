from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from mobile_api.schemas import ReplayStateResponse
from src.simulator.environment import TradingEnvironment


@dataclass
class ReplaySession:
    environment: TradingEnvironment
    revision: int = 0
    command_results: dict[str, ReplayStateResponse] = field(default_factory=dict)


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ReplaySession] = {}
        self._lock = RLock()

    @property
    def lock(self) -> RLock:
        return self._lock

    def put(self, session_id: str, session: ReplaySession) -> None:
        with self._lock:
            self._sessions[session_id] = session

    def get(self, session_id: str) -> ReplaySession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


session_store = InMemorySessionStore()
