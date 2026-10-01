from simon.kv_store import KeyValueStore, get_default_store
from simon.storage import upsert_session

PROGRESS_KEY = "change_word_progress_v1"
_EMPTY_PROGRESS = {"sessions": []}


class ChangeWordProgressStore:
    def __init__(self, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._data = self._store.load(PROGRESS_KEY, _EMPTY_PROGRESS)

    def _save(self) -> None:
        self._store.save(PROGRESS_KEY, self._data)

    def save_session(
        self,
        session_id: str,
        pairs_shown: list[str],
        changes_solved: int,
        first_words_solved: int,
        hints_used: int,
        revealed_count: int,
    ) -> None:
        """Saved after every word finished (see upsert_session), so leaving
        mid-game keeps the progress so far."""
        upsert_session(
            self._data["sessions"],
            session_id,
            {
                "pairs_shown": list(pairs_shown),
                "changes_solved": changes_solved,
                "first_words_solved": first_words_solved,
                "hints_used": hints_used,
                "revealed_count": revealed_count,
            },
        )
        self._save()

    def last_session(self) -> dict | None:
        sessions = self._data["sessions"]
        return sessions[-1] if sessions else None

    def seen_history(self) -> list[list[str]]:
        """The riddle pairs shown in each past game, oldest first -- used to
        show the player material they haven't seen yet."""
        return [s.get("pairs_shown", []) for s in self._data["sessions"]]

    def recent_sessions(self, n: int = 10) -> list[dict]:
        return self._data["sessions"][-n:]

    def best_changes_solved(self) -> int | None:
        counts = [s["changes_solved"] for s in self._data["sessions"]]
        return max(counts, default=None)
