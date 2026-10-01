import flet as ft

from simon.app_state import AppState
from simon.change_word_session import ChangeWordSession
from simon.letter_puzzle import GuessResult
from simon.screens.hebrew_keyboard import hebrew_keyboard
from simon.ui_helpers import GAME_THEMES, TEXT_SECONDARY, chip_button, content_width, game_header, primary_button, rtl_text

THEME = GAME_THEMES["change_word"]
SLOT_EMPTY_COLOR = "#FFFFFF"
SLOT_SOLVED_COLOR = "#D3F9D8"
FEEDBACK_WRONG = "כמעט! נסו מילה אחרת (אפשר למחוק עם ⌫)"


def build_change_word_game_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.change_word_session
    if session is None:
        session = ChangeWordSession(
            state.change_word_pairs, seen_history=state.change_word_progress.seen_history()
        )
        state.change_word_session = session

    width = content_width(page)
    progress_label = rtl_text("", size=16)
    # The whole riddle -- 'change "<clue 1>" into "<clue 2>"' -- is shown
    # from the start so the player knows where both stages are heading;
    # the line for the current stage is highlighted.
    riddle_lines = [
        ft.Container(content=rtl_text("", size=19), border_radius=12, padding=ft.Padding(10, 6, 10, 6), width=width - 16)
        for _ in range(2)
    ]
    riddle_box = ft.Container(
        content=ft.Column(riddle_lines, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
        bgcolor="#FFFFFF",
        border=ft.Border.all(2, THEME["light"]),
        border_radius=16,
        padding=6,
        width=width,
    )
    stage_label = rtl_text("", size=18, weight=ft.FontWeight.BOLD)
    extra_clue_label = rtl_text("", size=17, color=THEME["accent"])
    slot_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6)
    feedback_label = rtl_text("", size=18)

    def build_slots() -> None:
        slot_row.controls = [
            ft.Container(
                content=rtl_text("", size=28, weight=ft.FontWeight.BOLD),
                bgcolor=SLOT_EMPTY_COLOR,
                border=ft.Border.all(2, THEME["accent"]),
                border_radius=10,
                width=46,
                height=50,
                alignment=ft.Alignment(0, 0),
            )
            for _ in range(session.puzzle.length)
        ]

    def render_all() -> None:
        puzzle = session.puzzle
        progress_label.value = f"זוג {session.position} מתוך {session.total_pairs}"
        first, second = session.first, session.second
        first_found = session.stage == 2
        line_texts = [
            f'שנו את "{first["clue"]}"' + (f" = {first['word']} ✔" if first_found else ""),
            f'ל"{second["clue"]}"',
        ]
        for stage, (line, text) in enumerate(zip(riddle_lines, line_texts), start=1):
            active = stage == session.stage
            line.content.value = text
            line.content.weight = ft.FontWeight.BOLD if active else None
            line.content.color = THEME["accent"] if active else TEXT_SECONDARY
            line.bgcolor = THEME["light"] if active else None
        if session.stage == 1:
            stage_label.value = "שלב 1: מה המילה של השורה הראשונה?"
        else:
            stage_label.value = f'שלב 2: סדרו מחדש את האותיות של "{first["word"]}"'
        extra_clue_label.value = f"\U0001f4a1 {session.current['hint']}"
        extra_clue_label.visible = session.extra_clue_shown

        for slot, letter in zip(slot_row.controls, puzzle.slot_letters()):
            slot.content.value = letter
            if puzzle.solved:
                slot.bgcolor = SLOT_SOLVED_COLOR
            elif puzzle.revealed:
                slot.bgcolor = THEME["light"]
            else:
                slot.bgcolor = SLOT_EMPTY_COLOR

        playing_controls.visible = not puzzle.done
        next_button.visible = puzzle.done
        if session.stage == 1:
            next_button.content.value = "לשלב הבא"
        elif session.has_next_pair:
            next_button.content.value = "הזוג הבא"
        else:
            next_button.content.value = "לסיכום"

    def show_result(result: GuessResult) -> None:
        if result == GuessResult.CORRECT:
            if session.stage == 1:
                feedback_label.value = f'מצוין! המילה היא "{session.puzzle.answer}" \U0001f44f'
            else:
                feedback_label.value = "כל הכבוד! מצאת את המילה החדשה \U0001f389"
            save_progress()
        elif result == GuessResult.WRONG:
            feedback_label.value = FEEDBACK_WRONG
        else:
            feedback_label.value = ""

    def refresh() -> None:
        render_all()
        page.update()

    def on_letter(letter: str) -> None:
        session.puzzle.type_letter(letter)
        show_result(session.puzzle.check_attempt())
        refresh()

    def on_backspace() -> None:
        session.puzzle.backspace()
        feedback_label.value = ""
        refresh()

    async def clear(_: ft.ControlEvent) -> None:
        session.puzzle.clear()
        feedback_label.value = ""
        refresh()

    async def extra_clue(_: ft.ControlEvent) -> None:
        session.show_extra_clue()
        refresh()

    async def hint_letter(_: ft.ControlEvent) -> None:
        session.puzzle.hint_next_letter()
        show_result(session.puzzle.check_attempt())
        if not session.puzzle.done:
            feedback_label.value = "הוספנו לכם את האות הבאה"
        refresh()

    async def reveal(_: ft.ControlEvent) -> None:
        session.puzzle.reveal()
        feedback_label.value = f'המילה היא: "{session.puzzle.answer}"'
        save_progress()
        refresh()

    def save_progress() -> None:
        state.change_word_progress.save_session(
            session.log_id,
            pairs_shown=session.pairs_shown,
            changes_solved=session.changes_solved,
            first_words_solved=session.first_words_solved,
            hints_used=session.hints_used,
            revealed_count=session.revealed_count,
        )

    async def finish_session(_: ft.ControlEvent) -> None:
        save_progress()
        await page.push_route("/change/summary")

    async def next_step(e: ft.ControlEvent) -> None:
        if session.stage == 1:
            session.next_stage()
        elif session.has_next_pair:
            session.next_pair()
        else:
            await finish_session(e)
            return
        build_slots()
        feedback_label.value = ""
        refresh()

    async def exit_to_home(_: ft.ControlEvent) -> None:
        state.change_word_session = None
        await page.push_route("/")

    playing_controls = ft.Column(
        [
            hebrew_keyboard(on_letter, on_backspace, THEME["accent"], width),
            ft.Container(height=4),
            ft.Row(
                [
                    chip_button("נקה", clear, THEME["accent"]),
                    chip_button("רמז נוסף", extra_clue, THEME["accent"]),
                    chip_button("רמז: אות", hint_letter, THEME["accent"]),
                    chip_button("גלה מילה", reveal, THEME["accent"]),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                wrap=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )
    next_button = primary_button("", next_step, THEME["accent"])

    build_slots()
    render_all()

    return ft.View(
        route="/change",
        controls=[
            ft.Column(
                [
                    game_header(f"שינוי מילים {THEME['icon']}", THEME["accent"], "חזרה לתפריט", exit_to_home, finish_session),
                    progress_label,
                    riddle_box,
                    stage_label,
                    extra_clue_label,
                    ft.Container(content=slot_row, padding=ft.Padding(0, 4, 0, 0)),
                    feedback_label,
                    playing_controls,
                    next_button,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
