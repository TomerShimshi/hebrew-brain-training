"""The public app's anonymous usage counter: daily totals only, in its own
database -- never the family's -- and never able to break a game."""

import asyncio
import json
import sys
import types
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
import simon.kv_store as kv_store  # noqa: E402
import simon.usage_stats as usage_stats  # noqa: E402
from simon.app_state import AppState  # noqa: E402
from simon.usage_stats import (  # noqa: E402
    NEW_VISITOR,
    PLAYED,
    RETURNING_VISITOR,
    VISIT,
    UsageStats,
    game_event,
    get_usage_stats,
    record_visitor,
    visitor_event,
)

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


class FakePrefs:
    """The browser's local storage."""

    def __init__(self, values: dict | None = None) -> None:
        self.values = dict(values or {})

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value) -> bool:
        self.values[key] = value
        return True


class BrokenPrefs:
    async def get(self, key):
        raise RuntimeError("no storage in this browser")

    async def set(self, key, value):
        raise RuntimeError("no storage in this browser")


class FakePage:
    def __init__(self, route: str) -> None:
        self.route = route
        self.views: list = []
        self.window = types.SimpleNamespace(width=None, height=None)
        self.width = 390
        self.shared_preferences = FakePrefs()

    def update(self) -> None:
        pass

    def run_task(self, handler, *args):
        asyncio.run(handler(*args))


def test_opening_a_game_route_counts_it(public_env, requests, configured, monkeypatch):
    monkeypatch.setattr(kv_store, "_local_storage_dir", lambda: Path("unused"))
    page = FakePage("/definition")
    main.main(page)
    events = [body[2] for _url, body in requests]
    assert events == [VISIT, NEW_VISITOR, game_event("definition"), PLAYED]


def test_usage_page_is_family_only(public_env, requests):
    page = FakePage("/usage")
    main.main(page)
    assert page.views[0].route == "/"


DAY = date(2026, 11, 1)


def test_visitor_event_new_returning_or_already_counted_today():
    assert visitor_event(None, DAY) == NEW_VISITOR
    assert visitor_event((DAY - timedelta(days=3)).isoformat(), DAY) == RETURNING_VISITOR
    assert visitor_event(DAY.isoformat(), DAY) is None


def test_a_browser_is_counted_once_a_day_new_then_returning(requests):
    stats, prefs = UsageStats(USAGE_URL, "t"), FakePrefs()
    asyncio.run(record_visitor(stats, prefs, day=DAY))
    asyncio.run(record_visitor(stats, prefs, day=DAY))  # refresh, new tab, reconnect
    asyncio.run(record_visitor(stats, prefs, day=DAY + timedelta(days=1)))
    assert [(body[1], body[2]) for _url, body in requests] == [
        ("usage:2026-11-01", NEW_VISITOR),
        ("usage:2026-11-02", RETURNING_VISITOR),
    ]


def test_the_browser_keeps_only_a_date(requests):
    prefs = FakePrefs()
    asyncio.run(record_visitor(UsageStats(USAGE_URL, "t"), prefs, day=DAY))
    assert list(prefs.values.values()) == ["2026-11-01"]


def test_no_browser_storage_never_raises(requests):
    asyncio.run(record_visitor(UsageStats(USAGE_URL, "t"), BrokenPrefs(), day=DAY))
    assert requests == []


@pytest.fixture
def public_env(monkeypatch):
    monkeypatch.setenv("APP_MODE", "public")


def _texts(control) -> list[str]:
    found = [control.value] if isinstance(getattr(control, "value", None), str) else []
    for attr in ("content", "controls"):
        child = getattr(control, attr, None)
        for c in child if isinstance(child, list) else [child] if child is not None else []:
            found += _texts(c)
    return found


def test_usage_page_shows_different_visitors_new_and_returning():
    from simon.screens.usage_view import _report

    days = [
        (DAY, {VISIT: 9, PLAYED: 6, NEW_VISITOR: 3, RETURNING_VISITOR: 2}),
        (DAY - timedelta(days=1), {VISIT: 4, NEW_VISITOR: 2}),
    ]
    texts = [t for control in _report(days) for t in _texts(control)]
    assert "מבקרים שונים: 7 (חדשים 5 · חוזרים 2)" in texts
    assert "1.11 · 9 ביקורים · 5 מבקרים · 6 שיחקו" in texts
