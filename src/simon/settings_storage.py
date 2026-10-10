from datetime import date, timedelta

from simon.kv_store import KeyValueStore, get_default_store
from simon.word_levels import LEVELS, REGULAR

SETTINGS_KEY = "settings_v1"
_DEFAULTS = {"word_level": REGULAR, "suggestion_declines": []}

# declining a level suggestion this many times within PAUSE_DAYS pauses
# suggestions until PAUSE_DAYS after the last decline -- never nag
DECLINES_TO_PAUSE = 2
PAUSE_DAYS = 7


class SettingsStore:
    """Per-profile preferences that should survive between visits: the
    chosen word level, and recent "not now" answers to level suggestions."""

    def __init__(self, store: KeyValueStore | None = None) -> None:
        self._store = store or get_default_store()
        self._data = {**_DEFAULTS, **self._store.load(SETTINGS_KEY, _DEFAULTS)}

    @property
    def word_level(self) -> str:
        level = self._data["word_level"]
        return level if level in LEVELS else REGULAR

    @word_level.setter
    def word_level(self, level: str) -> None:
        if level not in LEVELS:
            raise ValueError(f"unknown word level: {level}")
        self._data["word_level"] = level
        self._store.save(SETTINGS_KEY, self._data)

    def record_suggestion_declined(self, today: date | None = None) -> None:
        today = today or date.today()
        declines = [*self._data["suggestion_declines"], today.isoformat()]
        self._data["suggestion_declines"] = declines[-DECLINES_TO_PAUSE:]
        self._store.save(SETTINGS_KEY, self._data)

    def suggestions_paused(self, today: date | None = None) -> bool:
        """True while level suggestions should stay quiet: the player said
        "not now" DECLINES_TO_PAUSE times within PAUSE_DAYS, and PAUSE_DAYS
        haven't passed since the last of those."""
        today = today or date.today()
        declines = [date.fromisoformat(d) for d in self._data["suggestion_declines"]]
        if len(declines) < DECLINES_TO_PAUSE:
            return False
        first, last = declines[-DECLINES_TO_PAUSE], declines[-1]
        return (last - first) <= timedelta(days=PAUSE_DAYS) and today < last + timedelta(days=PAUSE_DAYS)
