from simon.kv_store import KeyValueStore, get_default_store
from simon.storage import upsert_session

PROGRESS_KEY = "memory_progress_v1"
_EMPTY_PROGRESS = {"sessions": []}


class MemoryProgressStore:
    def __init__(self, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._data = self._store.load(PROGRESS_KEY, _EMPTY_PROGRESS)

    def _save(self) -> None:
        self._store.save(PROGRESS_KEY, self._data)

    def save_session(
        self,
        session_id: str,
        pair_count: int,
        moves: int,
        mismatches: int,
        completed: bool,
    ) -> None:
        """Saved after every matched pair (see upsert_session), so leaving
        mid-game keeps the play so far."""
        upsert_session(
            self._data["sessions"],
            session_id,
            {
                "pair_count": pair_count,
                "moves": moves,
                "mismatches": mismatches,
                "completed": completed,
            },
        )
        self._save()

    def _completed_sessions(self) -> list[dict]:
        # a half-played grid has fewer moves than any full one, so counting
        # it would look like a record -- scores and trends use only grids
        # that were finished (records saved before this flag existed were
        # only ever written on completion)
        return [s for s in self._data["sessions"] if s.get("completed", True)]

    def last_session(self) -> dict | None:
        sessions = self._completed_sessions()
        return sessions[-1] if sessions else None

    def recent_sessions(self, n: int = 10) -> list[dict]:
        return self._completed_sessions()[-n:]

    def best_moves_for(self, pair_count: int) -> int | None:
        """Fewest moves ever taken to complete a grid of this exact size --
        move counts aren't comparable across different grid sizes, so the
        record is tracked per size rather than as one overall best."""
        moves = [
            s["moves"] for s in self._completed_sessions() if s["pair_count"] == pair_count
        ]
        return min(moves, default=None)
