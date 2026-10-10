import flet as ft

from simon.app_state import AppState
from simon.scramble_session import ScrambleSession
from simon.screens.level_suggestion import current_offer, decline, level_suggestion_card
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text
from simon.word_levels import topic_words

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
            topic_words(state.scramble_categories[category], session.level),
            seen_history=state.scramble_progress.seen_history(),
            level=session.level,
        )
        await page.push_route("/scramble/play")

    # the game may end right when a level change is due -- offer it here too
    offer = current_offer(state, session) if session else None
    if offer and not topic_words(state.scramble_categories[session.category], offer.target_level):
        offer = None
    suggestion_slot = ft.Container(visible=offer is not None)

    async def accept_suggestion(_: ft.ControlEvent) -> None:
        level = offer.target_level
        state.settings.word_level = level
        state.scramble_session = ScrambleSession(
            session.category,
            topic_words(state.scramble_categories[session.category], level),
            seen_history=state.scramble_progress.seen_history(),
            level=level,
        )
        await page.push_route("/scramble/play")

    async def decline_suggestion(_: ft.ControlEvent) -> None:
        decline(state, session)
        suggestion_slot.visible = False
        page.update()

    if offer:
        suggestion_slot.content = level_suggestion_card(
            offer, session.clean_streak, "מילים", THEME["accent"], THEME["light"], accept_suggestion, decline_suggestion
        )

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
                    ft.Container(height=16),
                    suggestion_slot,
                    ft.Container(height=16),
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
