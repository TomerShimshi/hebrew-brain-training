import flet as ft

from simon.app_state import AppState
from simon.choice_games import ChoiceGame
from simon.screens.choice_game import new_choice_session
from simon.screens.level_suggestion import current_offer, decline, level_suggestion_card
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text


def build_choice_summary_view(page: ft.Page, state: AppState, game: ChoiceGame) -> ft.View:
    theme = GAME_THEMES[game.theme_key]
    session = state.choice_sessions.get(game.key)
    first_try = session.first_try_correct if session else 0
    answered = session.answered if session else 0
    best = state.choice_progress[game.key].best_first_try_correct()
    is_new_best = not state.public and first_try > 0 and first_try >= (best or 0)

    async def new_game(_: ft.ControlEvent) -> None:
        level = session.level if session else state.word_level
        state.choice_sessions[game.key] = new_choice_session(state, game, level)
        await page.push_route(game.route)

    # the game may end right when a level change is due -- offer it here too
    offer = current_offer(state, session) if session else None
    if offer and len(state.choice_items[game.key][offer.target_level]) < 4:
        offer = None
    suggestion_slot = ft.Container(visible=offer is not None)

    async def accept_suggestion(_: ft.ControlEvent) -> None:
        level = offer.target_level
        state.settings.word_level = level
        state.choice_sessions[game.key] = new_choice_session(state, game, level)
        await page.push_route(game.route)

    async def decline_suggestion(_: ft.ControlEvent) -> None:
        decline(state, session)
        suggestion_slot.visible = False
        page.update()

    if offer:
        suggestion_slot.content = level_suggestion_card(
            offer, session.clean_streak, "שאלות", theme["accent"], theme["light"], accept_suggestion, decline_suggestion
        )

    async def go_home(_: ft.ControlEvent) -> None:
        state.choice_sessions[game.key] = None
        await page.push_route("/")

    return ft.View(
        route=f"{game.route}/summary",
        controls=[
            ft.Column(
                [
                    rtl_text(
                        f"{theme['icon']} " + ("שיא חדש!" if is_new_best else "כל הכבוד!"),
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        color=theme["accent"],
                    ),
                    ft.Container(height=16),
                    rtl_text(f"ענית נכון בניסיון הראשון על {first_try} מתוך {answered}", size=22),
                    ft.Container(height=8),
                    rtl_text(f"השיא שלך: {best}", size=18) if best and not state.public else ft.Container(),
                    ft.Container(height=16),
                    suggestion_slot,
                    ft.Container(height=16),
                    primary_button("משחק חדש", new_game, theme["accent"]),
                    ft.Container(height=12),
                    chip_button("חזרה לתפריט", go_home, theme["accent"]),
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
