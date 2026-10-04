import flet as ft

from simon.app_state import AppState
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text

THEME = GAME_THEMES["subword"]


def build_subword_summary_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.subword_session
    count = session.total_found_count if session else 0
    hints_used = session.hints_used if session else 0
    best = state.subword_progress.best_words_found_count()
    is_new_best = not state.public and count > 0 and count >= (best or 0)

    async def play_again(_: ft.ControlEvent) -> None:
        state.subword_session = None
        await page.push_route("/subword")

    async def go_home(_: ft.ControlEvent) -> None:
        state.subword_session = None
        await page.push_route("/")

    return ft.View(
        route="/subword/summary",
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
                    rtl_text(f"מצאת {count} מילים", size=24),
                    ft.Container(height=8),
                    rtl_text(f"השיא שלך: {best}", size=18) if best and not state.public else ft.Container(),
                    rtl_text(f"רמזים שנעשה בהם שימוש: {hints_used}", size=14) if hints_used else ft.Container(),
                    ft.Container(height=32),
                    primary_button("משחק חדש", play_again, THEME["accent"]),
                    ft.Container(height=12),
                    chip_button("חזרה לתפריט", go_home, THEME["accent"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
