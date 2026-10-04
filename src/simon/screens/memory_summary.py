import flet as ft

from simon.app_state import AppState
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text

THEME = GAME_THEMES["memory"]


def build_memory_summary_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.memory_session
    moves = session.moves if session else 0
    pair_count = session.pair_count if session else 0
    best_moves = state.memory_progress.best_moves_for(pair_count) if session else None
    is_new_best = not state.public and session is not None and moves == best_moves

    async def play_again(_: ft.ControlEvent) -> None:
        state.memory_session = None
        await page.push_route("/memory")

    async def go_home(_: ft.ControlEvent) -> None:
        state.memory_session = None
        await page.push_route("/")

    return ft.View(
        route="/memory/summary",
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
                    rtl_text(f"מספר הצעדים שלך: {moves}", size=24),
                    ft.Container(height=8),
                    rtl_text(
                        f"השיא שלך בגודל הזה: {best_moves}" if best_moves and not state.public else "",
                        size=20,
                    ),
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
