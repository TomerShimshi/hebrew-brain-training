"""The card that offers a change of word level (see level_suggestions),
shared by the scrambled-words and change-a-word screens and summaries."""

import flet as ft

from simon.app_state import AppState
from simon.level_suggestions import Suggestion
from simon.ui_helpers import chip_button, rtl_text

CARD_WIDTH = 330


def current_offer(state: AppState, session) -> Suggestion | None:
    """The suggestion to show now, if any -- none while the player's recent
    "not now" answers have paused suggestions."""
    if state.settings.suggestions_paused():
        return None
    return session.level_suggestion()


def decline(state: AppState, session) -> None:
    """"Not now": no more offers in this game, and it counts toward the
    week-long pause after repeated declines."""
    session.suggestion_dismissed = True
    state.settings.record_suggestion_declined()


def level_suggestion_card(
    suggestion: Suggestion,
    streak: int,
    unit: str,
    color: str,
    light: str,
    on_accept,
    on_decline,
) -> ft.Container:
    """A gentle, non-blocking card -- the game carries on if it's ignored.
    `unit` names what was solved ("מילים" / "חידות")."""
    if suggestion is Suggestion.UP:
        message = f"\U0001f31f כל הכבוד! פתרת {streak} {unit} ברצף.\nרוצה לנסות את הרמה המתקדמת?"
        accept_label, decline_label = "כן, בוא ננסה", "לא עכשיו"
    else:
        message = "\U0001f4aa המילים ברמה הזאת לא פשוטות.\nרוצה לעבור לרמה הרגילה לבינתיים?"
        accept_label, decline_label = "כן, לרמה הרגילה", "להמשיך כאן"

    accept_button = ft.Container(
        content=rtl_text(accept_label, size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        bgcolor=color,
        border_radius=20,
        padding=ft.Padding(18, 10, 18, 10),
        on_click=on_accept,
        ink=True,
    )
    return ft.Container(
        content=ft.Column(
            [
                rtl_text(message, size=17, weight=ft.FontWeight.W_600),
                ft.Row(
                    [accept_button, chip_button(decline_label, on_decline, color)],
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True,
                    spacing=10,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        bgcolor=light,
        border=ft.Border.all(2, color),
        border_radius=16,
        padding=14,
        width=CARD_WIDTH,
    )


def show_view(page: ft.Page, view: ft.View) -> None:
    """Swaps in a freshly built view for the current route -- used to start
    a new game at the new level without leaving the screen (pushing the
    same route again wouldn't rebuild it)."""
    page.views.clear()
    page.views.append(view)
    page.update()
