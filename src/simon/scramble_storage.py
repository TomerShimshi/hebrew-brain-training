from simon.kv_store import KeyValueStore, get_default_store
from simon.storage import upsert_session
from simon.word_levels import REGULAR

PROGRESS_KEY = "scramble_progress_v1"
_EMPTY_PROGRESS = {"sessions": []}


class ScrambleProgressStore:
    def __init__(self, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._data = self._store.load(PROGRESS_KEY, _EMPTY_PROGRESS)

    def _save(self) -> None:
        self._store.save(PROGRESS_KEY, self._data)

    def save_session(
        self,
        session_id: str,
        category: str,
        words_shown: list[str],
        words_solved_count: int,
        hints_used: int,
        revealed_count: int,
        level: str = REGULAR,
    ) -> None:
        upsert_session(
            self._data["sessions"],
            session_id,
            {
                "category": category,
                "words_shown": list(words_shown),
                "words_solved_count": words_solved_count,
                "hints_used": hints_used,
                "revealed_count": revealed_count,
                "level": level,
            },
        )
        self._save()

    def last_session(self) -> dict | None:
        sessions = self._data["sessions"]
        return sessions[-1] if sessions else None

    def seen_history(self) -> list[list[str]]:
        """The words shown in each past game, oldest first -- used to
        show the player material they haven't seen yet."""
        return [s.get("words_shown", []) for s in self._data["sessions"]]

    def recent_sessions(self, n: int = 10) -> list[dict]:
        return self._data["sessions"][-n:]

    def best_words_solved_count(self) -> int | None:
        counts = [s["words_solved_count"] for s in self._data["sessions"]]
        return max(counts, default=None)
