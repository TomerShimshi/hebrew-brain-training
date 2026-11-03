"""The home screen: every game is a tile in a two-column grid, grouped into
memory games and word games, with the word-level switch in the word-games
section -- so the whole menu fits a phone in about a screen and a half."""

import asyncio
import types

import simon.app_state as app_state_module
from simon.app_state import AppState
from simon.choice_games import CHOICE_GAMES
from simon.kv_store import InMemoryKeyValueStore
from simon.screens.home import build_home_view

GAME_ROUTES = {
    "simon": "/simon",
    "memory": "/memory",
    "subword": "/subword",
    "scramble": "/scramble",
    "change_word": "/change",
    **{game.key: game.route for game in CHOICE_GAMES.values()},
}
MEMORY_GAMES = {"simon", "memory"}
WORD_GAMES = set(GAME_ROUTES) - MEMORY_GAMES
PHONE_CONTENT_WIDTH = 330  # a 360px phone less the page's side padding


class FakePage:
    def __init__(self) -> None:
        self.route = "/"
        self.views: list = []
        self.width = 360
        self.window = types.SimpleNamespace(width=None, height=None)

    def update(self) -> None:
        pass

    async def push_route(self, route: str) -> None:
        self.route = route


def _walk(control):
    yield control
    for attr in ("controls", "content"):
        child = getattr(control, attr, None)
        if isinstance(child, list):
            for c in child:
                yield from _walk(c)
        elif child is not None and hasattr(child, "__dict__"):
            yield from _walk(child)


def _with_data(root, prefix: str) -> dict:
    return {c.data.removeprefix(prefix): c for c in _walk(root) if str(getattr(c, "data", "")).startswith(prefix)}


def _home(monkeypatch, public: bool = False):
    monkeypatch.setattr(app_state_module, "get_default_store", lambda: InMemoryKeyValueStore())
    if public:
        monkeypatch.setenv("APP_MODE", "public")
    else:
        monkeypatch.delenv("APP_MODE", raising=False)
    state = AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})
    if public:
        state.activate_guest()
    else:
        state.activate_profile("other")
    page = FakePage()
    return state, page, build_home_view(page, state)


def test_every_game_has_a_tile_that_opens_it(monkeypatch):
    _state, page, view = _home(monkeypatch)
    tiles = _with_data(view, "game:")
    assert set(tiles) == set(GAME_ROUTES)
    for key, route in GAME_ROUTES.items():
        asyncio.run(tiles[key].on_click(None))
        assert page.route == route


def test_games_are_grouped_and_the_level_switch_is_with_the_word_games(monkeypatch):
    _state, _page, view = _home(monkeypatch)
    sections = _with_data(view, "section:")
    assert set(_with_data(sections["memory"], "game:")) == MEMORY_GAMES
    assert set(_with_data(sections["words"], "game:")) == WORD_GAMES
    assert _with_data(sections["words"], "level-switch")
    assert not _with_data(sections["memory"], "level-switch")


def test_two_tiles_fit_side_by_side_on_a_phone(monkeypatch):
    _state, _page, view = _home(monkeypatch)
    rows = [c for c in _walk(view) if getattr(c, "data", None) == "tile-row"]
    assert rows
    for row in rows:
        assert len(row.controls) <= 2
        assert sum(t.width for t in row.controls) + row.spacing * (len(row.controls) - 1) <= PHONE_CONTENT_WIDTH


def test_family_tiles_show_a_short_last_time_line(monkeypatch):
    state, _page, _view = _home(monkeypatch)
    state.progress.last_session = lambda: {"best_length": 3}
    view = build_home_view(FakePage(), state)
    captions = _with_data(view, "caption:")
    assert set(captions) == set(GAME_ROUTES)
    assert captions["simon"].value == "רצף 3"


def test_public_tiles_show_no_last_time_line(monkeypatch):
    _state, _page, view = _home(monkeypatch, public=True)
    assert set(_with_data(view, "game:")) == set(GAME_ROUTES)
    assert _with_data(view, "caption:") == {}
