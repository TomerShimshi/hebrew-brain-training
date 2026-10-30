from simon.kv_store import KeyValueStore, get_default_store
from simon.storage import upsert_session
from simon.word_levels import REGULAR

_EMPTY_PROGRESS = {"sessions": []}


class ChoiceProgressStore:
    """Progress for one multiple-choice game (synonym, opposite,
    definition) -- each game keeps its own record under its own key."""

    def __init__(self, game_key: str, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._key = f"{game_key}_progress_v1"
        self._data = self._store.load(self._key, _EMPTY_PROGRESS)

    def _save(self) -> None:
        self._store.save(self._key, self._data)

    def save_session(
        self,
        session_id: str,
        answers_shown: list[str],
        first_try_correct: int,
        answered: int,
        level: str = REGULAR,
    ) -> None:
        upsert_session(
            self._data["sessions"],
            session_id,
            {
                "answers_shown": list(answers_shown),
                "first_try_correct": first_try_correct,
                "answered": answered,
                "level": level,
            },
        )
        self._save()

    def last_session(self) -> dict | None:
        sessions = self._data["sessions"]
        return sessions[-1] if sessions else None

    def seen_history(self) -> list[list[str]]:
        """The answers shown in each past game, oldest first -- used to
        ask the player questions they haven't seen yet."""
        return [s.get("answers_shown", []) for s in self._data["sessions"]]

    def recent_sessions(self, n: int = 10) -> list[dict]:
        return self._data["sessions"][-n:]

    def best_first_try_correct(self) -> int | None:
        return max((s["first_try_correct"] for s in self._data["sessions"]), default=None)
