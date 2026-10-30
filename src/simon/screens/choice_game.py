import flet as ft

from simon.app_state import AppState
from simon.choice_games import ChoiceGame
from simon.choice_session import ChoiceSession
from simon.screens.level_suggestion import current_offer, decline, level_suggestion_card, show_view
from simon.ui_helpers import GAME_THEMES, TEXT_PRIMARY, content_width, game_header, primary_button, rtl_text
from simon.word_levels import ADVANCED
from simon.word_levels import LABELS as LEVEL_LABELS

WRONG_COLOR = "#FFE3E3"
RIGHT_COLOR = "#D3F9D8"
RIGHT_BORDER = "#2F9E44"
FEEDBACK_WRONG = "לא בדיוק, נסו שוב"
FEEDBACK_RIGHT = "מצוין! \U0001f389"


def new_choice_session(state: AppState, game: ChoiceGame, level: str) -> ChoiceSession:
    return ChoiceSession(
        state.choice_items[game.key][level],
        seen_history=state.choice_progress[game.key].seen_history(),
        level=level,
    )


def save_choice_progress(state: AppState, game: ChoiceGame, session: ChoiceSession) -> None:
    state.choice_progress[game.key].save_session(
        session.log_id,
        answers_shown=session.answers_shown,
        first_try_correct=session.first_try_correct,
        answered=session.answered,
        level=session.level,
    )


def build_choice_game_view(page: ft.Page, state: AppState, game: ChoiceGame) -> ft.View:
    theme = GAME_THEMES[game.theme_key]
    session = state.choice_sessions.get(game.key)
    if session is None:
        # a fresh game from the home screen, or a browser refresh
        session = new_choice_session(state, game, state.word_level)
        state.choice_sessions[game.key] = session
    width = content_width(page)
    # a definition is a sentence; a word gets a big, bold card
    is_definition = game.key == "definition"

    progress_label = rtl_text("", size=16)
    prompt_label = rtl_text("", size=22 if is_definition else 34, weight=None if is_definition else ft.FontWeight.BOLD)
    prompt_card = ft.Container(
        content=prompt_label,
        bgcolor=theme["light"],
        border_radius=16,
        padding=ft.Padding(16, 18, 16, 18),
        width=width,
        alignment=ft.Alignment(0, 0),
    )
    options_column = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    feedback_label = rtl_text("", size=18, weight=ft.FontWeight.W_600, color=theme["accent"])
    feedback_label.data = "feedback"

    def option_button(option: str) -> ft.Container:
        is_answer = option == session.item.answer
        if option in session.picked:
            color, border = (RIGHT_COLOR, RIGHT_BORDER) if is_answer else (WRONG_COLOR, WRONG_COLOR)
        else:
            color, border = "#FFFFFF", theme["light"]

        async def on_click(_: ft.ControlEvent) -> None:
            pick(option)

        return ft.Container(
            content=rtl_text(option, size=22, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
            data=("option", option),
            bgcolor=color,
            border=ft.Border.all(2, border),
            border_radius=16,
            padding=ft.Padding(14, 16, 14, 16),
            width=width,
            alignment=ft.Alignment(0, 0),
            disabled=session.done or option in session.picked,
            on_click=on_click,
            ink=True,
        )

    def render_all() -> None:
        level_note = f" · {LEVEL_LABELS[session.level]}" if session.level == ADVANCED else ""
        progress_label.value = f"שאלה {session.position} מתוך {session.total}{level_note}"
        prompt_label.value = session.item.prompt
        options_column.controls = [option_button(option) for option in session.options]
        next_button.visible = session.done
        next_button.content.value = "השאלה הבאה" if session.has_next else "לסיכום"
        render_suggestion()

    # the "move up / move down a level?" card -- shown after an answered
    # question, never mid-question, and the game carries on if it's ignored
    suggestion_slot = ft.Container(visible=False)
    shown_offer = {"key": None}

    def offer_now():
        offer = current_offer(state, session) if session.done else None
        return offer if offer and len(state.choice_items[game.key][offer.target_level]) >= 4 else None

    def render_suggestion() -> None:
        offer = offer_now()
        key = (offer, session.clean_streak)  # rebuild when the streak in the text grows
        if key != shown_offer["key"]:
            shown_offer["key"] = key
            if offer:
                suggestion_slot.content = level_suggestion_card(
                    offer, session.clean_streak, "שאלות", theme["accent"], theme["light"],
                    accept_suggestion, decline_suggestion,
                )
        suggestion_slot.visible = offer is not None

    async def accept_suggestion(_: ft.ControlEvent) -> None:
        offer = offer_now()
        if offer is None:
            return
        level = offer.target_level
        state.settings.word_level = level
        state.choice_sessions[game.key] = new_choice_session(state, game, level)
        show_view(page, build_choice_game_view(page, state, game))

    async def decline_suggestion(_: ft.ControlEvent) -> None:
        decline(state, session)
        render_all()
        page.update()

    def pick(option: str) -> None:
        if session.done or option in session.picked:
            return
        if session.pick(option):
            feedback_label.value = FEEDBACK_RIGHT
            save_choice_progress(state, game, session)
        else:
            feedback_label.value = FEEDBACK_WRONG
        render_all()
        page.update()

    async def finish(_: ft.ControlEvent) -> None:
        if session.answered:
            save_choice_progress(state, game, session)
        await page.push_route(f"{game.route}/summary")

    async def next_question(e: ft.ControlEvent) -> None:
        if not session.has_next:
            await finish(e)
            return
        session.next_question()
        feedback_label.value = ""
        render_all()
        page.update()

    async def exit_to_menu(_: ft.ControlEvent) -> None:
        # every answer is already saved, so leaving mid-game loses nothing
        state.choice_sessions[game.key] = None
        await page.push_route("/")

    header = game_header(f"{game.title} {theme['icon']}", theme["accent"], "חזרה לתפריט", exit_to_menu, finish)
    header.controls[0].data = "exit"
    next_button = primary_button("השאלה הבאה", next_question, theme["accent"])
    next_button.data = "next"

    render_all()

    return ft.View(
        route=game.route,
        controls=[
            ft.Column(
                [
                    header,
                    progress_label,
                    rtl_text(game.prompt_line, size=18),
                    prompt_card,
                    options_column,
                    feedback_label,
                    suggestion_slot,
                    next_button,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
