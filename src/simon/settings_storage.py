from simon.kv_store import KeyValueStore, get_default_store
from simon.word_levels import LEVELS, REGULAR

SETTINGS_KEY = "settings_v1"
_DEFAULTS = {"word_level": REGULAR}


class SettingsStore:
    """Per-profile preferences that should survive between visits, like the
    chosen word level."""

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
