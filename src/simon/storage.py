import uuid
from datetime import datetime, timezone

from simon.kv_store import KeyValueStore, get_default_store

PROGRESS_KEY = "progress_v1"
_EMPTY_PROGRESS = {"sessions": []}

DEFAULT_STEP_MS = 900
MIN_STEP_MS = 500
MAX_STEP_MS = 1100
SESSIONS_FOR_ADAPTATION = 3


class ProgressStore:
    def __init__(self, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._data = self._store.load(PROGRESS_KEY, _EMPTY_PROGRESS)

    def _save(self) -> None:
        self._store.save(PROGRESS_KEY, self._data)

    def save_session(
        self,
        session_id: str,
        best_length: int,
        rounds_played: int,
        rounds_correct: int,
        step_ms: int,
    ) -> None:
        """Saved after every round (see upsert_session), so leaving
        mid-game keeps the rounds played so far."""
        upsert_session(
            self._data["sessions"],
            session_id,
            {
                "best_length": best_length,
                "rounds_played": rounds_played,
                "rounds_correct": rounds_correct,
                "step_ms": step_ms,
            },
        )
        self._save()

    def last_session(self) -> dict | None:
        sessions = self._data["sessions"]
        return sessions[-1] if sessions else None

    def best_length_ever(self) -> int:
        sessions = self._data["sessions"]
        return max((s["best_length"] for s in sessions), default=0)

    def recent_sessions(self, n: int = SESSIONS_FOR_ADAPTATION) -> list[dict]:
        return self._data["sessions"][-n:]

    def adaptive_step_ms(self) -> int:
        """Returns the playback speed (ms per flash) for a new session.

        Every session always starts a fresh sequence at length 1 -- a stroke
        survivor re-practicing memory should get the same clean restart each
        time, not be dropped into a longer sequence because a past session
        went well. Only *playback speed* adapts: faster after recent strong
        accuracy, slower after recent struggling, so no caregiver has to
        tune a difficulty setting by hand.
        """
        recent = self.recent_sessions()
        if not recent:
            return DEFAULT_STEP_MS

        total_played = sum(s["rounds_played"] for s in recent)
        total_correct = sum(s["rounds_correct"] for s in recent)
        avg_accuracy = total_correct / total_played if total_played else 0.0

        step_ms = DEFAULT_STEP_MS
        if avg_accuracy >= 0.75:
            step_ms -= 150
        elif avg_accuracy < 0.6:
            step_ms += 150
        return max(MIN_STEP_MS, min(MAX_STEP_MS, step_ms))


def new_session_id() -> str:
    return str(uuid.uuid4())


def upsert_session(sessions: list[dict], session_id: str, fields: dict) -> None:
    """Adds the session's record the first time it's saved and updates it
    in place after that. Every game saves after each bit of progress (a
    round, a matched pair, a found word), so progress survives the player
    leaving mid-game -- and because a session keeps one id throughout, it
    is never counted twice."""
    existing = next((s for s in sessions if s["id"] == session_id), None)
    if existing is None:
        sessions.append({"id": session_id, "date": datetime.now(timezone.utc).isoformat(), **fields})
    else:
        existing.update(fields)
