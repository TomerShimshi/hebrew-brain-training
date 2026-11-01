import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import functools

import flet as ft

from simon.app_mode import is_public_mode
from simon.app_state import AppState
from simon.change_word_bank import load_all_pairs
from simon.choice_games import CHOICE_GAMES, load_choice_items
from simon.screens.change_word_game import build_change_word_game_view
from simon.screens.change_word_summary import build_change_word_summary_view
from simon.screens.choice_game import build_choice_game_view
from simon.screens.choice_summary import build_choice_summary_view
from simon.screens.home import build_home_view
from simon.screens.memory_game import build_memory_game_view
from simon.screens.memory_summary import build_memory_summary_view
from simon.screens.profile_picker import build_profile_picker_view
from simon.screens.progress_view import build_progress_view
from simon.screens.scramble_categories import build_scramble_categories_view
from simon.screens.scramble_game import build_scramble_game_view
from simon.screens.scramble_summary import build_scramble_summary_view
from simon.screens.simon_game import build_simon_game_view
from simon.screens.simon_summary import build_simon_summary_view
from simon.screens.subword_game import build_subword_game_view
from simon.screens.subword_summary import build_subword_summary_view
from simon.screens.usage_view import build_usage_view
from simon.scramble_bank import load_categories
from simon.subword_bank import load_bank, load_clues
from simon.ui_helpers import BACKGROUND
from simon.usage_stats import record_visitor
from simon.user_profile import profile_from_route, route_path

ROUTE_BUILDERS = {
    "/": build_home_view,
    "/simon": build_simon_game_view,
    "/simon/summary": build_simon_summary_view,
    "/memory": build_memory_game_view,
    "/memory/summary": build_memory_summary_view,
    "/subword": build_subword_game_view,
    "/subword/summary": build_subword_summary_view,
    "/scramble": build_scramble_categories_view,
    "/scramble/play": build_scramble_game_view,
    "/scramble/summary": build_scramble_summary_view,
    "/change": build_change_word_game_view,
    "/change/summary": build_change_word_summary_view,
    "/progress": build_progress_view,
    "/usage": build_usage_view,
}
# the three multiple-choice games share their screens (see choice_games)
for _game in CHOICE_GAMES.values():
    ROUTE_BUILDERS[_game.route] = functools.partial(build_choice_game_view, game=_game)
    ROUTE_BUILDERS[f"{_game.route}/summary"] = functools.partial(build_choice_summary_view, game=_game)
# Browser tab / window title -- also used for the web page shell (web.py), so
# the tab names the app even while it's still loading.
APP_TITLE = "Hebrew Brain Training"

# Screens built on saved history -- not reachable in the public app.
FAMILY_ONLY_ROUTES = {"/progress", "/usage"}

# The route that starts each game -> its key in the public app's usage
# counts (see usage_stats). Opening one counts as starting that game.
GAME_START_ROUTES = {
    "/simon": "simon",
    "/memory": "memory",
    "/subword": "subword",
    "/scramble/play": "scramble",
    "/change": "change_word",
    **{game.route: game.key for game in CHOICE_GAMES.values()},
}


def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BACKGROUND
    page.window.width = 420
    page.window.height = 780

    categories = load_categories()
    state = AppState(
        subword_bank=load_bank(),
        subword_clues=load_clues(),
        scramble_categories=categories,
        change_word_pairs=load_all_pairs(),
        choice_items=load_choice_items(categories),
    )

    def render_current_route(*_args) -> None:
        # reset per-screen handlers so a stale closure from the previous
        # screen never outlives its view
        page.on_resize = None
        page.views.clear()

        if state.profile is None:
            if is_public_mode():
                # no profiles in the public app: every visitor is an
                # anonymous guest whose play is never saved
                state.activate_guest()
                if state.usage:
                    page.run_task(record_visitor, state.usage, page.shared_preferences)
            else:
                requested = profile_from_route(page.route)
                if requested:
                    state.activate_profile(requested)
                else:
                    page.views.append(build_profile_picker_view(page, state))
                    page.update()
                    return

        path = route_path(page.route)
        if state.public and path in FAMILY_ONLY_ROUTES:
            path = "/"
        builder = ROUTE_BUILDERS.get(path, build_home_view)
        if path in GAME_START_ROUTES:
            state.record_game_started(GAME_START_ROUTES[path])
        page.views.append(builder(page, state))
        page.update()

    page.on_route_change = render_current_route
    render_current_route()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
