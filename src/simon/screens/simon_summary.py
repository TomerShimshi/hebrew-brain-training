import flet as ft

from simon.app_state import AppState
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text

THEME = GAME_THEMES["simon"]


def build_simon_summary_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.session
    current_streak = session.best_length if session else 0
    best_streak = state.progress.best_length_ever()
    is_new_best = not state.public and current_streak > 0 and current_streak >= best_streak

    async def play_again(_: ft.ControlEvent) -> None:
        state.session = None
        await page.push_route("/simon")

    async def go_home(_: ft.ControlEvent) -> None:
        state.session = None
        await page.push_route("/")

    return ft.View(
        route="/simon/summary",
        controls=[
            ft.Column(
                [
                    rtl_text(
                        f"{THEME['icon']} " + ("שיא חדש!" if is_new_best else "כל הכבוד!"),
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        color=THEME["accent"],
                    ),
                    ft.Container(height=16),
                    rtl_text(f"הרצף הנוכחי שלך: {current_streak}", size=24),
                    ft.Container(height=8),
                    rtl_text(f"השיא שלך: {best_streak}", size=20) if not state.public else ft.Container(),
                    ft.Container(height=32),
                    primary_button("משחק חדש", play_again, THEME["accent"]),
                    ft.Container(height=12),
                    chip_button("חזרה לתפריט", go_home, THEME["accent"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
