"""The choice-game screen: a wrong pick greys that option out and the
question stays open; the right pick finishes it, saves progress and shows
the next button."""

import asyncio
import random
import types

import simon.app_state as app_state_module
import simon.screens.choice_game as choice_game
from simon.app_state import AppState
from simon.choice_bank import ChoiceItem
from simon.choice_games import CHOICE_GAMES
from simon.choice_session import ChoiceSession
from simon.kv_store import InMemoryKeyValueStore

GAME = CHOICE_GAMES["opposite"]


class FakePage:
    def __init__(self) -> None:
        self.route = GAME.route
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


def _find(view, data):
    return next(c for c in _walk(view) if getattr(c, "data", None) == data)


def _start(monkeypatch):
    monkeypatch.setattr(app_state_module, "get_default_store", lambda: InMemoryKeyValueStore())
    state = AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})
    state.activate_profile("other")
    items = [ChoiceItem(f"מילה{i}", f"תשובה{i}", "", frozenset({f"תשובה{i}"})) for i in range(10)]
    session = ChoiceSession(items, rng=random.Random(1))
    state.choice_sessions[GAME.key] = session
    page = FakePage()
    view = choice_game.build_choice_game_view(page, state, GAME)
    return state, session, page, view


def _click(control):
    asyncio.run(control.on_click(None))


def _wrong(session):
    return next(o for o in session.options if o != session.item.answer)


def test_wrong_then_right_pick_flow(monkeypatch):
    state, session, page, view = _start(monkeypatch)
    next_button = _find(view, "next")
    assert not next_button.visible

    wrong = _wrong(session)
    _click(_find(view, ("option", wrong)))
    assert _find(view, "feedback").value == "לא בדיוק, נסו שוב"
    assert _find(view, ("option", wrong)).bgcolor == "#FFE3E3"
    assert _find(view, ("option", wrong)).disabled
    assert not next_button.visible

    _click(_find(view, ("option", session.item.answer)))
    assert _find(view, "feedback").value == "מצוין! \U0001f389"
    assert _find(view, ("option", session.item.answer)).bgcolor == "#D3F9D8"
    assert all(_find(view, ("option", o)).disabled for o in session.options)
    assert next_button.visible

    _click(next_button)
    assert session.position == 2
    assert _find(view, "feedback").value == ""
    assert not next_button.visible
    assert not any(_find(view, ("option", o)).disabled for o in session.options)


def test_progress_saved_after_each_answer(monkeypatch):
    state, session, page, view = _start(monkeypatch)
    store = state.choice_progress[GAME.key]
    _click(_find(view, ("option", _wrong(session))))
    assert store.last_session() is None
    _click(_find(view, ("option", session.item.answer)))
    assert store.last_session()["answered"] == 1
    assert store.last_session()["first_try_correct"] == 0
    _click(_find(view, "next"))
    _click(_find(view, ("option", session.item.answer)))
    last = store.last_session()
    assert (last["answered"], last["first_try_correct"]) == (2, 1)
    assert len(store.recent_sessions()) == 1


def test_leaving_mid_game_keeps_progress(monkeypatch):
    state, session, page, view = _start(monkeypatch)
    _click(_find(view, ("option", session.item.answer)))
    _click(_find(view, "next"))
    _click(_find(view, "exit"))
    assert page.route == "/"
    assert state.choice_sessions[GAME.key] is None
    assert state.choice_progress[GAME.key].last_session()["answered"] == 1
