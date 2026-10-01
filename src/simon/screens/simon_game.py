import asyncio

import flet as ft

from simon.app_state import AppState
from simon.audio import SoundBoard
from simon.models import COLORS
from simon.session_manager import SimonSession
from simon.ui_helpers import GAME_THEMES, PAD_COLORS, PAD_COLORS_LIT, chip_button, game_header, rtl_text, soft_shadow

THEME = GAME_THEMES["simon"]

STEP_GAP_S = 0.3  # silent gap between playback steps, on top of session.step_ms
INTER_ROUND_PAUSE_S = 1.1
TAP_HIGHLIGHT_MS = 350


def _play_sound(coro) -> None:
    """Fires a sound coroutine without awaiting it, so a slow/hung/broken
    audio backend can never stall or crash the game loop -- audio is a
    nice-to-have here, gameplay timing and scoring must never depend on it."""
    task = asyncio.ensure_future(coro)
    task.add_done_callback(lambda t: t.exception())


def build_simon_game_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.session
    if session is None:
        session = SimonSession(start_length=1, step_ms=state.progress.adaptive_step_ms())
        state.session = session

    sound = SoundBoard()
    lock = {"busy": True}  # pads ignore taps until the sequence finishes playing
    player_input: list[int] = []

    status_label = rtl_text("שים לב לרצף...", size=24, weight=ft.FontWeight.BOLD)
    length_label = rtl_text(f"אורך: {session.current_length}", size=16)
    pads: dict[int, ft.Container] = {}

    def set_pad_lit(index: int, lit: bool) -> None:
        color = COLORS[index]
        pads[index].bgcolor = PAD_COLORS_LIT[color] if lit else PAD_COLORS[color]

    def build_pad(index: int) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            await handle_pad_tap(index)

        pad = ft.Container(
            bgcolor=PAD_COLORS[COLORS[index]],
            border_radius=20,
            expand=True,
            on_click=on_click,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            shadow=soft_shadow(PAD_COLORS[COLORS[index]], opacity=0.35, blur=10),
        )
        pads[index] = pad
        return pad

    board = ft.Column(
        [
            ft.Row([build_pad(0), build_pad(1)], expand=True, spacing=16),
            ft.Row([build_pad(2), build_pad(3)], expand=True, spacing=16),
        ],
        expand=True,
        spacing=16,
    )

    async def flash_pad(index: int, duration_ms: int) -> None:
        set_pad_lit(index, True)
        _play_sound(sound.play_color(index))
        page.update()
        await asyncio.sleep(duration_ms / 1000)
        set_pad_lit(index, False)
        page.update()

    async def play_sequence() -> None:
        lock["busy"] = True
        player_input.clear()
        status_label.value = "שים לב לרצף..."
        length_label.value = f"אורך: {session.current_length}"
        page.update()
        await asyncio.sleep(0.6)
        for color_index in session.sequence:
            await flash_pad(color_index, session.step_ms)
            await asyncio.sleep(STEP_GAP_S)
        status_label.value = "עכשיו תורך!"
        page.update()
        lock["busy"] = False

    def save_progress() -> None:
        state.progress.save_session(
            session.log_id,
            best_length=session.best_length,
            rounds_played=session.rounds_played,
            rounds_correct=session.rounds_correct,
            step_ms=session.step_ms,
        )

    async def finish_session() -> None:
        save_progress()
        await page.push_route("/simon/summary")

    async def handle_pad_tap(index: int) -> None:
        if lock["busy"] or session.finished:
            return
        lock["busy"] = True
        await flash_pad(index, TAP_HIGHLIGHT_MS)
        player_input.append(index)

        step = len(player_input) - 1
        if session.sequence[step] != index:
            _play_sound(sound.play_error())
            session.record_round(False)
            save_progress()
            if session.finished:
                status_label.value = "הפעם לא הצלחנו..."
                page.update()
                await asyncio.sleep(INTER_ROUND_PAUSE_S)
                await finish_session()
                return
            status_label.value = "לא נורא, ננסה שוב פעם אחת!"
            page.update()
            await asyncio.sleep(INTER_ROUND_PAUSE_S)
            await play_sequence()
            return

        if len(player_input) == session.current_length:
            status_label.value = "מצוין!"
            page.update()
            session.record_round(True)
            save_progress()
            await asyncio.sleep(INTER_ROUND_PAUSE_S)
            if session.finished:
                await finish_session()
                return
            await play_sequence()
            return

        lock["busy"] = False

    async def exit_to_home(_: ft.ControlEvent) -> None:
        state.session = None
        await page.push_route("/")

    async def end_session_now(_: ft.ControlEvent) -> None:
        if session.rounds_played > 0:
            await finish_session()
        else:
            await exit_to_home(_)

    page.run_task(play_sequence)

    return ft.View(
        route="/simon",
        services=sound.controls,
        controls=[
            ft.Column(
                [
                    game_header(f"סיימון {THEME['icon']}", THEME["accent"], "חזרה לתפריט", exit_to_home, end_session_now),
                    status_label,
                    length_label,
                    ft.Container(content=board, expand=True, padding=16),
                ],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
