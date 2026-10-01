import flet as ft

from simon.app_state import AppState
from simon.letter_puzzle import GuessResult
from simon.screens.letter_board import LetterBoard
from simon.ui_helpers import GAME_THEMES, chip_button, game_header, primary_button, rtl_text

THEME = GAME_THEMES["scramble"]
TILE_USED_COLOR = "#C9BCF5"
FEEDBACK_SOLVED = "מצוין! סידרת את המילה \U0001f389"
FEEDBACK_WRONG = "כמעט! נסו לסדר אחרת (אפשר ללחוץ על \"ביטול\")"


def build_scramble_game_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.scramble_session
    if session is None:
        # e.g. a browser refresh on /scramble/play -- no category chosen yet
        return _redirect_to_categories(page)

    icon = state.scramble_categories[session.category]["icon"]

    progress_label = rtl_text("", size=16)
    feedback_label = rtl_text("", size=18)
    clue_label = rtl_text("", size=18, weight=ft.FontWeight.W_600, color=THEME["accent"])
    clue_box = ft.Container(
        content=clue_label,
        bgcolor=THEME["light"],
        border_radius=14,
        padding=ft.Padding(16, 10, 16, 10),
        width=330,
    )

    def render_all() -> None:
        progress_label.value = f"{icon} {session.category} · מילה {session.position} מתוך {session.total_words}"
        board.render()
        # once asked for, the clue stays up for the rest of the word so the
        # player can keep glancing back at it while arranging letters
        clue_box.visible = session.clue_shown
        playing_controls.visible = not session.puzzle.done
        next_button.visible = session.puzzle.done
        next_button.content.value = "המילה הבאה" if session.has_next_word else "לסיכום"

    def show_result(result: GuessResult) -> None:
        if result == GuessResult.CORRECT:
            feedback_label.value = FEEDBACK_SOLVED
            save_progress()
        elif result == GuessResult.WRONG:
            feedback_label.value = FEEDBACK_WRONG
        else:
            feedback_label.value = ""

    def on_tile_tap(result: GuessResult) -> None:
        show_result(result)
        render_all()

    board = LetterBoard(page, THEME["accent"], THEME["light"], TILE_USED_COLOR, on_tile_tap)

    async def undo(_: ft.ControlEvent) -> None:
        session.puzzle.undo_last()
        feedback_label.value = ""
        render_all()
        page.update()

    async def clear(_: ft.ControlEvent) -> None:
        session.puzzle.clear_attempt()
        feedback_label.value = ""
        render_all()
        page.update()

    async def hint(_: ft.ControlEvent) -> None:
        session.puzzle.hint_next_letter()
        show_result(session.puzzle.check_attempt())
        if not session.puzzle.done:
            feedback_label.value = "הוספנו לכם את האות הבאה"
        render_all()
        page.update()

    async def show_clue(_: ft.ControlEvent) -> None:
        clue_label.value = f"\U0001f4a1 {session.get_clue()}"
        render_all()
        page.update()

    async def reveal(_: ft.ControlEvent) -> None:
        session.puzzle.reveal()
        feedback_label.value = f'המילה היא: "{session.answer}"'
        render_all()
        page.update()

    def save_progress() -> None:
        state.scramble_progress.save_session(
            session.log_id,
            category=session.category,
            words_shown=session.words_shown,
            words_solved_count=session.solved_count,
            hints_used=session.hints_used,
            revealed_count=session.revealed_count,
        )

    async def finish_session(_: ft.ControlEvent) -> None:
        save_progress()
        await page.push_route("/scramble/summary")

    async def next_word(e: ft.ControlEvent) -> None:
        if not session.has_next_word:
            await finish_session(e)
            return
        session.next_word()
        board.set_puzzle(session.puzzle)
        feedback_label.value = ""
        render_all()
        page.update()

    async def exit_to_categories(_: ft.ControlEvent) -> None:
        state.scramble_session = None
        await page.push_route("/scramble")

    playing_controls = ft.Column(
        [
            ft.Row(
                [
                    chip_button("ביטול", undo, THEME["accent"]),
                    chip_button("נקה", clear, THEME["accent"]),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True,
            ),
            ft.Row(
                [
                    chip_button("רמז: מה המילה?", show_clue, THEME["accent"]),
                    chip_button("רמז: אות נוספת", hint, THEME["accent"]),
                    chip_button("גלה מילה", reveal, THEME["accent"]),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
    )
    next_button = primary_button("המילה הבאה", next_word, THEME["accent"])

    board.set_puzzle(session.puzzle)
    render_all()

    return ft.View(
        route="/scramble/play",
        controls=[
            ft.Column(
                [
                    game_header(f"מילים מבולגנות {THEME['icon']}", THEME["accent"], "נושאים", exit_to_categories, finish_session),
                    progress_label,
                    rtl_text("סדרו את האותיות למילה", size=18),
                    clue_box,
                    board.control,
                    feedback_label,
                    playing_controls,
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


def _redirect_to_categories(page: ft.Page) -> ft.View:
    async def go(_: ft.ControlEvent) -> None:
        await page.push_route("/scramble")

    return ft.View(
        route="/scramble/play",
        controls=[primary_button("בחירת נושא", go, THEME["accent"])],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
