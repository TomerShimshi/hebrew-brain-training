import flet as ft

from simon.app_state import AppState
from simon.scramble_session import ScrambleSession
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text

THEME = GAME_THEMES["scramble"]


def build_scramble_summary_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.scramble_session
    solved = session.solved_count if session else 0
    shown = len(session.words_shown) if session else 0
    hints_used = session.hints_used if session else 0
    best = state.scramble_progress.best_words_solved_count()
    is_new_best = not state.public and solved > 0 and solved >= (best or 0)

    async def same_category(_: ft.ControlEvent) -> None:
        category = session.category
        state.scramble_session = ScrambleSession(
            category,
            state.scramble_categories[category]["words"],
            seen_history=state.scramble_progress.seen_history(),
        )
        await page.push_route("/scramble/play")

    async def other_category(_: ft.ControlEvent) -> None:
        state.scramble_session = None
        await page.push_route("/scramble")

    async def go_home(_: ft.ControlEvent) -> None:
        state.scramble_session = None
        await page.push_route("/")

    return ft.View(
        route="/scramble/summary",
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
                    rtl_text(f"סידרת {solved} מילים מתוך {shown}", size=24),
                    rtl_text(f"נושא: {session.category}", size=18) if session else ft.Container(),
                    ft.Container(height=8),
                    rtl_text(f"השיא שלך: {best}", size=18) if best and not state.public else ft.Container(),
                    rtl_text(f"רמזים שנעשה בהם שימוש: {hints_used}", size=14) if hints_used else ft.Container(),
                    ft.Container(height=32),
                    primary_button("שוב באותו נושא", same_category, THEME["accent"])
                    if session
                    else ft.Container(),
                    ft.Container(height=12),
                    chip_button("נושא אחר", other_category, THEME["accent"]),
                    ft.Container(height=8),
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
