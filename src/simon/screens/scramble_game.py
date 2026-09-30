import flet as ft

from simon.app_state import AppState
from simon.scramble_session import GuessResult
from simon.ui_helpers import GAME_THEMES, chip_button, primary_button, rtl_text, soft_shadow

THEME = GAME_THEMES["scramble"]
TILE_COLOR = THEME["accent"]
TILE_USED_COLOR = "#C9BCF5"
SLOT_EMPTY_COLOR = "#FFFFFF"
SLOT_SOLVED_COLOR = "#D3F9D8"
SLOT_REVEALED_COLOR = THEME["light"]
FEEDBACK_SOLVED = "מצוין! סידרת את המילה \U0001f389"


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
    slot_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6, wrap=True, run_spacing=6)
    tile_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10, wrap=True, run_spacing=10)
    tiles: dict[int, ft.Container] = {}
    slots: list[ft.Container] = []

    def build_tile(index: int) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            session.tap_tile(index)
            auto_check()
            render_all()
            page.update()

        tile = ft.Container(
            content=rtl_text(session.tiles[index], size=30, color="#FFFFFF"),
            bgcolor=TILE_COLOR,
            border_radius=14,
            width=60,
            height=60,
            alignment=ft.Alignment(0, 0),
            on_click=on_click,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            shadow=soft_shadow(TILE_COLOR, opacity=0.3, blur=8),
        )
        tiles[index] = tile
        return tile

    def build_slot() -> ft.Container:
        slot = ft.Container(
            content=rtl_text("", size=28, weight=ft.FontWeight.BOLD),
            bgcolor=SLOT_EMPTY_COLOR,
            border=ft.Border.all(2, THEME["accent"]),
            border_radius=10,
            width=48,
            height=56,
            alignment=ft.Alignment(0, 0),
        )
        slots.append(slot)
        return slot

    def rebuild_word() -> None:
        tiles.clear()
        slots.clear()
        tile_row.controls = [build_tile(i) for i in range(len(session.tiles))]
        slot_row.controls = [build_slot() for _ in session.tiles]

    def render_all() -> None:
        progress_label.value = f"{icon} {session.category} · מילה {session.position} מתוך {session.total_words}"
        for i, tile in tiles.items():
            tile.bgcolor = TILE_USED_COLOR if i in session.current_attempt else TILE_COLOR
        for slot, letter in zip(slots, session.slot_letters()):
            slot.content.value = letter
            if not session.word_done:
                slot.bgcolor = SLOT_EMPTY_COLOR
            else:
                slot.bgcolor = SLOT_REVEALED_COLOR if session.word_revealed else SLOT_SOLVED_COLOR
        # once asked for, the clue stays up for the rest of the word so the
        # player can keep glancing back at it while arranging letters
        clue_box.visible = session.clue_shown
        playing_controls.visible = not session.word_done
        next_button.visible = session.word_done
        next_button.content.value = "המילה הבאה" if session.has_next_word else "לסיכום"

    def auto_check() -> None:
        # the answer's length is visible as slots, so checking the moment
        # the last slot fills saves a button press without any surprise
        result = session.check_attempt()
        if result == GuessResult.CORRECT:
            feedback_label.value = FEEDBACK_SOLVED
            save_progress()
        elif result == GuessResult.WRONG:
            feedback_label.value = "כמעט! נסו לסדר אחרת (אפשר ללחוץ על \"ביטול\")"
        else:
            feedback_label.value = ""

    async def undo(_: ft.ControlEvent) -> None:
        session.undo_last()
        feedback_label.value = ""
        render_all()
        page.update()

    async def clear(_: ft.ControlEvent) -> None:
        session.clear_attempt()
        feedback_label.value = ""
        render_all()
        page.update()

    async def hint(_: ft.ControlEvent) -> None:
        session.hint_next_letter()
        auto_check()
        if not session.word_done:
            feedback_label.value = "הוספנו לכם את האות הבאה"
        render_all()
        page.update()

    async def show_clue(_: ft.ControlEvent) -> None:
        clue_label.value = f"\U0001f4a1 {session.get_clue()}"
        render_all()
        page.update()

    async def reveal(_: ft.ControlEvent) -> None:
        session.reveal_word()
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
        rebuild_word()
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

    rebuild_word()
    render_all()

    return ft.View(
        route="/scramble/play",
        controls=[
            ft.Column(
                [
                    ft.Row(
                        [
                            chip_button("נושאים", exit_to_categories, THEME["accent"]),
                            rtl_text(f"מילים מבולגנות {THEME['icon']}", size=20, weight=ft.FontWeight.BOLD),
                            chip_button("סיום", finish_session, THEME["accent"]),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    progress_label,
                    rtl_text("סדרו את האותיות למילה", size=18),
                    clue_box,
                    ft.Container(content=slot_row, padding=ft.Padding(0, 12, 0, 4)),
                    ft.Container(content=tile_row, padding=16),
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
