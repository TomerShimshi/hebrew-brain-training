from dataclasses import dataclass

from simon.change_word_session import ChangeWordSession
from simon.change_word_storage import ChangeWordProgressStore
from simon.engagement_storage import EngagementStore
from simon.kv_store import InMemoryKeyValueStore, KeyValueStore, NamespacedKeyValueStore, get_default_store
from simon.memory_session import MemoryGameSession
from simon.memory_storage import MemoryProgressStore
from simon.scramble_session import ScrambleSession
from simon.scramble_storage import ScrambleProgressStore
from simon.session_manager import SimonSession
from simon.settings_storage import SettingsStore
from simon.storage import ProgressStore
from simon.subword_session import SubWordSession
from simon.subword_storage import SubWordProgressStore


@dataclass
class AppState:
    subword_bank: dict[str, list[str]]
    subword_clues: dict[str, str]
    scramble_categories: dict[str, dict]
    # word level (see word_levels) -> that level's riddle pairs
    change_word_pairs: dict[str, list[list[dict]]]

    # None until a profile is chosen on the picker screen -- main.py's
    # routing gates every other screen on `profile` being set, so by the
    # time any game screen actually runs, these are guaranteed populated.
    profile: str | None = None
    # True in the public app: screens hide everything history-based
    # (streaks, records, "last time" captions, the progress screen).
    public: bool = False
    progress: ProgressStore | None = None
    memory_progress: MemoryProgressStore | None = None
    subword_progress: SubWordProgressStore | None = None
    scramble_progress: ScrambleProgressStore | None = None
    change_word_progress: ChangeWordProgressStore | None = None
    engagement: EngagementStore | None = None
    settings: SettingsStore | None = None

    session: SimonSession | None = None
    memory_session: MemoryGameSession | None = None
    subword_session: SubWordSession | None = None
    scramble_session: ScrambleSession | None = None
    change_word_session: ChangeWordSession | None = None

    def activate_profile(self, profile: str) -> None:
        """Gives this profile its own namespaced view of the storage
        backend, so e.g. "efraim" and "tomer" never see each other's
        progress even though they share the same Upstash database."""
        self.profile = profile
        self._attach_stores(NamespacedKeyValueStore(get_default_store(), profile))
        self.engagement.record_visit()

    def activate_guest(self) -> None:
        """Public mode (see app_mode): this visit gets its own throwaway
        in-memory storage, so the games still work within the visit (e.g.
        unseen words first) but nothing is saved or shared with anyone, and
        persistent storage is never touched."""
        self.public = True
        self.profile = "guest"
        self._attach_stores(InMemoryKeyValueStore())

    def _attach_stores(self, store: KeyValueStore) -> None:
        self.progress = ProgressStore(store=store)
        self.memory_progress = MemoryProgressStore(store=store)
        self.subword_progress = SubWordProgressStore(store=store)
        self.scramble_progress = ScrambleProgressStore(store=store)
        self.change_word_progress = ChangeWordProgressStore(store=store)
        self.engagement = EngagementStore(store=store)
        self.settings = SettingsStore(store=store)

    @property
    def word_level(self) -> str:
        return self.settings.word_level
