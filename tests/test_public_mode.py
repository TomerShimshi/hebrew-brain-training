"""The public app must keep nothing and reach nothing: no Upstash database,
no local files, no profile names, no history on screen."""

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
import simon.kv_store as kv_store  # noqa: E402
from simon.app_mode import is_public_mode  # noqa: E402
from simon.app_state import AppState  # noqa: E402
from simon.kv_store import InMemoryKeyValueStore, PublicModeStorageError, get_default_store  # noqa: E402


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setenv("APP_MODE", "public")


@pytest.fixture
def no_network_or_disk(monkeypatch, tmp_path):
    """Fails the test if anything tries to reach Upstash or write files."""
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "secret")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("public mode tried to reach persistent storage")

    monkeypatch.setattr(kv_store.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(kv_store, "_local_storage_dir", lambda: tmp_path)
    return tmp_path


def _state() -> AppState:
    return AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})


def test_mode_is_read_from_the_environment(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    assert not is_public_mode()
    for value in ["public", "PUBLIC", ' "public" ']:
        monkeypatch.setenv("APP_MODE", value)
        assert is_public_mode()
    monkeypatch.setenv("APP_MODE", "family")
    assert not is_public_mode()


def test_persistent_storage_refuses_to_open_in_public_mode(public, no_network_or_disk):
    # even with database credentials present by mistake
    with pytest.raises(PublicModeStorageError):
        get_default_store()


def test_guest_storage_is_in_memory_and_writes_nothing(public, no_network_or_disk):
    state = _state()
    state.activate_guest()
    assert state.public
    state.scramble_progress.save_session(
        "s1", category="אוכל", words_shown=["לחם"], words_solved_count=1, hints_used=0, revealed_count=0
    )
    assert state.scramble_progress.last_session()["words_solved_count"] == 1
    assert list(no_network_or_disk.iterdir()) == []


def test_each_visit_gets_its_own_storage(public, no_network_or_disk):
    first, second = _state(), _state()
    first.activate_guest()
    second.activate_guest()
    first.subword_progress.save_session("s1", base_words=["שלום"], words_found_count=3, hints_used=0)
    assert second.subword_progress.last_session() is None


def test_family_mode_still_uses_profiles_and_persistent_storage(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    backend = InMemoryKeyValueStore()
    monkeypatch.setattr("simon.app_state.get_default_store", lambda: backend)
    state = _state()
    state.activate_profile("tomer")
    assert not state.public
    state.subword_progress.save_session("s1", base_words=["שלום"], words_found_count=2, hints_used=0)
    assert backend.load("tomer:subword_progress_v1", {"sessions": []})["sessions"]


class FakePage:
    def __init__(self, route: str) -> None:
        self.route = route
        self.views: list = []
        self.window = types.SimpleNamespace(width=None, height=None)
        self.width = 390

    def update(self) -> None:
        pass


def _render(route: str) -> FakePage:
    page = FakePage(route)
    main.main(page)
    return page


def test_public_app_skips_the_profile_picker(public, no_network_or_disk):
    page = _render("/?user=tomer")  # a family bookmark doesn't unlock anything
    assert page.views[0].route == "/"


def test_public_app_hides_the_progress_screen(public, no_network_or_disk):
    page = _render("/progress")
    assert page.views[0].route == "/"


def test_family_app_still_asks_who_is_playing(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    page = _render("/")
    assert page.views[0].route == "/profile"
