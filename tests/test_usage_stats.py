"""The public app's anonymous usage counter: daily totals only, in its own
database -- never the family's -- and never able to break a game."""

import json
import sys
import types
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
import simon.kv_store as kv_store  # noqa: E402
import simon.usage_stats as usage_stats  # noqa: E402
from simon.app_state import AppState  # noqa: E402
from simon.usage_stats import PLAYED, VISIT, UsageStats, game_event, get_usage_stats  # noqa: E402

USAGE_URL = "https://usage.upstash.io"
FAMILY_URL = "https://family.upstash.io"


class FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


@pytest.fixture
def requests(monkeypatch):
    """Records every HTTP request instead of sending it."""
    sent = []

    def urlopen(req, timeout=None):
        sent.append((req.full_url, json.loads(req.data) if req.data else None))
        return FakeResponse({"result": 1})

    monkeypatch.setattr(usage_stats.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(kv_store.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(usage_stats, "_in_background", lambda job: job())
    return sent


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("USAGE_REDIS_REST_URL", USAGE_URL)
    monkeypatch.setenv("USAGE_REDIS_REST_TOKEN", "usage-secret")


def _state() -> AppState:
    return AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})


def test_record_adds_one_to_that_days_counter(requests):
    UsageStats(USAGE_URL, "t").record(VISIT, day=date(2026, 11, 1))
    assert requests == [(USAGE_URL, ["HINCRBY", "usage:2026-11-01", "visit", 1])]


def test_not_configured_means_no_counter(monkeypatch):
    monkeypatch.delenv("USAGE_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("USAGE_REDIS_REST_TOKEN", raising=False)
    assert get_usage_stats() is None


def test_family_app_reads_counts_with_its_own_database_keys(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.delenv("USAGE_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("USAGE_REDIS_REST_TOKEN", raising=False)
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", FAMILY_URL)
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "family-secret")
    assert get_usage_stats()._url == FAMILY_URL


def test_public_app_never_falls_back_to_the_family_keys(public_env, monkeypatch):
    monkeypatch.delenv("USAGE_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("USAGE_REDIS_REST_TOKEN", raising=False)
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", FAMILY_URL)
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "family-secret")
    assert get_usage_stats() is None


def test_a_failing_counter_never_raises(monkeypatch):
    def broken(*_args, **_kwargs):
        raise OSError("network down")

    monkeypatch.setattr(usage_stats.urllib.request, "urlopen", broken)
    monkeypatch.setattr(usage_stats, "_in_background", lambda job: job())
    stats = UsageStats(USAGE_URL, "t")
    stats.record(VISIT)
    assert stats.daily_counts(days=3) == []


def test_daily_counts_reads_each_day_newest_first(monkeypatch):
    def urlopen(req, timeout=None):
        assert req.full_url == f"{USAGE_URL}/pipeline"
        assert json.loads(req.data) == [["HGETALL", "usage:2026-11-01"], ["HGETALL", "usage:2026-10-31"]]
        return FakeResponse([{"result": ["visit", "5", "played", "3", "game:opposite", "2"]}, {"result": []}])

    monkeypatch.setattr(usage_stats.urllib.request, "urlopen", urlopen)
    counts = UsageStats(USAGE_URL, "t").daily_counts(days=2, until=date(2026, 11, 1))
    assert counts == [
        (date(2026, 11, 1), {"visit": 5, "played": 3, "game:opposite": 2}),
        (date(2026, 10, 31), {}),
    ]


def test_public_visit_counts_visit_played_once_and_each_game(public_env, requests, configured):
    state = _state()
    state.activate_guest()
    state.record_game_started("opposite")
    state.record_game_started("simon")
    events = [body[2] for _url, body in requests]
    assert events == [VISIT, game_event("opposite"), PLAYED, game_event("simon")]


def test_counter_never_reaches_the_family_database(public_env, requests, configured, monkeypatch):
    # even if the family database's keys were given to the public service by mistake
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", FAMILY_URL)
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "family-secret")
    state = _state()
    state.activate_guest()
    state.record_game_started("synonym")
    assert requests
    for url, body in requests:
        assert url == USAGE_URL
        assert body[0] == "HINCRBY" and body[1].startswith("usage:")


def test_family_app_counts_nothing(monkeypatch, requests, configured):
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.setattr("simon.app_state.get_default_store", lambda: kv_store.InMemoryKeyValueStore())
    state = _state()
    state.activate_profile("tomer")
    state.record_game_started("simon")
    assert requests == []


class FakePage:
    def __init__(self, route: str) -> None:
        self.route = route
        self.views: list = []
        self.window = types.SimpleNamespace(width=None, height=None)
        self.width = 390

    def update(self) -> None:
        pass


def test_opening_a_game_route_counts_it(public_env, requests, configured, monkeypatch):
    monkeypatch.setattr(kv_store, "_local_storage_dir", lambda: Path("unused"))
    page = FakePage("/definition")
    main.main(page)
    events = [body[2] for _url, body in requests]
    assert events == [VISIT, game_event("definition"), PLAYED]


def test_usage_page_is_family_only(public_env, requests):
    page = FakePage("/usage")
    main.main(page)
    assert page.views[0].route == "/"


@pytest.fixture
def public_env(monkeypatch):
    monkeypatch.setenv("APP_MODE", "public")
