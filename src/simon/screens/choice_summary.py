import flet as ft

from simon.app_state import AppState
from simon.choice_games import ChoiceGame


def build_choice_summary_view(page: ft.Page, state: AppState, game: ChoiceGame) -> ft.View:
    return ft.View(route=f"{game.route}/summary")
