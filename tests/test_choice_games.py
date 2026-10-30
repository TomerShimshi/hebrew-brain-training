import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
from simon.app_state import AppState  # noqa: E402
from simon.choice_games import CHOICE_GAMES, load_choice_items  # noqa: E402
from simon.scramble_bank import load_categories  # noqa: E402
from simon.ui_helpers import GAME_THEMES  # noqa: E402
from simon.word_levels import LEVELS  # noqa: E402


def test_registry_has_the_three_games():
    assert list(CHOICE_GAMES) == ["synonym", "opposite", "definition"]
    assert CHOICE_GAMES["synonym"].title == "מילה נרדפת"
    assert CHOICE_GAMES["opposite"].prompt_line == "מה ההפך של המילה?"
    assert CHOICE_GAMES["definition"].route == "/definition"
    for game in CHOICE_GAMES.values():
        assert game.route == f"/{game.key}"
        assert game.theme_key in GAME_THEMES


def test_every_game_has_items_at_both_levels():
    items = load_choice_items(load_categories())
    for key in CHOICE_GAMES:
        for level in LEVELS:
            assert len(items[key][level]) >= 10, (key, level)


def test_routes_are_registered():
    for game in CHOICE_GAMES.values():
        assert game.route in main.ROUTE_BUILDERS
        assert f"{game.route}/summary" in main.ROUTE_BUILDERS


def test_public_mode_keeps_choice_progress_in_memory(monkeypatch, tmp_path):
    import simon.kv_store as kv_store

    monkeypatch.setenv("APP_MODE", "public")
    monkeypatch.setattr(kv_store, "_local_storage_dir", lambda: tmp_path)
    first = AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})
    second = AppState(subword_bank={}, subword_clues={}, scramble_categories={}, change_word_pairs={})
    first.activate_guest()
    second.activate_guest()
    first.choice_progress["synonym"].save_session("s1", ["קר"], 1, 1)
    assert first.choice_progress["synonym"].last_session()["first_try_correct"] == 1
    assert second.choice_progress["synonym"].last_session() is None
    assert first.choice_progress["opposite"].last_session() is None
    assert list(tmp_path.iterdir()) == []
