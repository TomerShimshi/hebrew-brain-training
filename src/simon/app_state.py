from dataclasses import dataclass

from simon.change_word_session import ChangeWordSession
from simon.change_word_storage import ChangeWordProgressStore
from simon.engagement_storage import EngagementStore
from simon.kv_store import NamespacedKeyValueStore, get_default_store
from simon.memory_session import MemoryGameSession
from simon.memory_storage import MemoryProgressStore
from simon.scramble_session import ScrambleSession
from simon.scramble_storage import ScrambleProgressStore
from simon.session_manager import SimonSession
from simon.storage import ProgressStore
from simon.subword_session import SubWordSession
from simon.subword_storage import SubWordProgressStore


@dataclass
class AppState:
    subword_bank: dict[str, list[str]]
    subword_clues: dict[str, str]
    scramble_categories: dict[str, dict]
    change_word_pairs: list[list[dict]]

    # None until a profile is chosen on the picker screen -- main.py's
    # routing gates every other screen on `profile` being set, so by the
    # time any game screen actually runs, these are guaranteed populated.
    profile: str | None = None
    progress: ProgressStore | None = None
    memory_progress: MemoryProgressStore | None = None
    subword_progress: SubWordProgressStore | None = None
    scramble_progress: ScrambleProgressStore | None = None
    change_word_progress: ChangeWordProgressStore | None = None
    engagement: EngagementStore | None = None

    session: SimonSession | None = None
    memory_session: MemoryGameSession | None = None
    subword_session: SubWordSession | None = None
    scramble_session: ScrambleSession | None = None
    change_word_session: ChangeWordSession | None = None

    def activate_profile(self, profile: str) -> None:
        """Gives this profile its own namespaced view of the storage
        backend, so e.g. "efraim" and "tomer" never see each other's
        progress even though they share the same Upstash database."""
        store = NamespacedKeyValueStore(get_default_store(), profile)
        self.profile = profile
        self.progress = ProgressStore(store=store)
        self.memory_progress = MemoryProgressStore(store=store)
        self.subword_progress = SubWordProgressStore(store=store)
        self.scramble_progress = ScrambleProgressStore(store=store)
        self.change_word_progress = ChangeWordProgressStore(store=store)
        self.engagement = EngagementStore(store=store)
        self.engagement.record_visit()
