"""Leaving the Simon screen mid-sequence must stop its background playback:
notes used to keep sounding after going back to the menu."""

import asyncio

import simon.app_state as app_state_module
import simon.audio as audio
import simon.screens.simon_game as simon_game
from simon.app_state import AppState
from simon.kv_store import InMemoryKeyValueStore
from simon.session_manager import SimonSession


class FakePage:
    def __init__(self) -> None:
        self.route = "/simon?user=other"

    def update(self) -> None:
        pass

    async def push_route(self, route: str) -> None:
        self.route = route

    def run_task(self, coroutine_function) -> None:
        self.task = asyncio.ensure_future(coroutine_function())


def _start_game(monkeypatch, notes: list):
    async def play_color(self, index):
        notes.append(asyncio.get_running_loop().time())

    async def loaded(self, timeout_s):
        return True

    async def stop_all(self, timeout_s=0.5):
        pass

    monkeypatch.setattr(audio.SoundBoard, "play_color", play_color)
    monkeypatch.setattr(audio.SoundBoard, "wait_until_loaded", loaded)
    monkeypatch.setattr(audio.SoundBoard, "stop_all", stop_all)
    monkeypatch.setattr(app_state_module, "get_default_store", lambda: InMemoryKeyValueStore())

    state = AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})
    state.activate_profile("other")
    state.session = SimonSession(start_length=6, step_ms=50)
    page = FakePage()
    view = simon_game.build_simon_game_view(page, state)
    back_button = view.controls[0].controls[0].controls[0]  # "חזרה לתפריט" in the header
    return page, back_button


def test_leaving_mid_sequence_stops_the_remaining_notes(monkeypatch):
    monkeypatch.setattr(simon_game, "STEP_GAP_S", 0.05)
    notes: list[float] = []

    async def scenario():
        page, back_button = _start_game(monkeypatch, notes)
        await asyncio.sleep(0.8)  # opening pause + a couple of notes
        played_before = len(notes)
        await back_button.on_click(None)
        await asyncio.sleep(1.0)  # longer than the rest of the sequence
        return played_before, len(notes), page.route

    played_before, played_total, route = asyncio.run(scenario())
    assert 0 < played_before < 6
    assert played_total == played_before  # nothing played after leaving
    assert route == "/"


def test_the_full_sequence_plays_when_the_player_stays(monkeypatch):
    monkeypatch.setattr(simon_game, "STEP_GAP_S", 0.05)
    notes: list[float] = []

    async def scenario():
        _start_game(monkeypatch, notes)
        await asyncio.sleep(2.0)

    asyncio.run(scenario())
    assert len(notes) == 6
