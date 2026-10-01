from simon.kv_store import KeyValueStore, get_default_store
from simon.storage import upsert_session

PROGRESS_KEY = "subword_progress_v1"
_EMPTY_PROGRESS = {"sessions": []}


class SubWordProgressStore:
    def __init__(self, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._data = self._store.load(PROGRESS_KEY, _EMPTY_PROGRESS)

    def _save(self) -> None:
        self._store.save(PROGRESS_KEY, self._data)

    def save_session(
        self,
        session_id: str,
        base_words: list[str],
        words_found_count: int,
        hints_used: int,
    ) -> None:
        """Saved after every word found (see upsert_session), so leaving
        mid-game keeps the words found so far."""
        upsert_session(
            self._data["sessions"],
            session_id,
            {
                "base_words": list(base_words),
                "words_found_count": words_found_count,
                "hints_used": hints_used,
            },
        )
        self._save()

    def last_session(self) -> dict | None:
        sessions = self._data["sessions"]
        return sessions[-1] if sessions else None

    def seen_history(self) -> list[list[str]]:
        """The base words shown in each past game, oldest first -- used to
        show the player material they haven't seen yet."""
        return [s.get("base_words", []) for s in self._data["sessions"]]

    def recent_sessions(self, n: int = 10) -> list[dict]:
        return self._data["sessions"][-n:]

    def best_words_found_count(self) -> int | None:
        counts = [s["words_found_count"] for s in self._data["sessions"]]
        return max(counts, default=None)
