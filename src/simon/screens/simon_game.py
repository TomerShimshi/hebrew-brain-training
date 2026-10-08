import asyncio
import sys

import flet as ft

from simon.app_state import AppState
from simon.audio import SoundBoard
from simon.models import COLORS
from simon.session_manager import SimonSession
from simon.ui_helpers import GAME_THEMES, PAD_COLORS, PAD_COLORS_LIT, chip_button, game_header, rtl_text, soft_shadow
from simon.user_profile import route_path

THEME = GAME_THEMES["simon"]

STEP_GAP_S = 0.3  # silent gap between playback steps, on top of session.step_ms
INTER_ROUND_PAUSE_S = 1.1
TAP_HIGHLIGHT_MS = 350


SOUND_LOAD_TIMEOUT_S = 5


def _log_sound_failure(task: asyncio.Task) -> None:
    error = task.exception()
    if error is not None:
        print(f"[audio] playback failed: {error!r}", file=sys.stderr)


def _play_sound(coro) -> None:
    """Fires a sound coroutine without awaiting it, so a slow/hung/broken
    audio backend can never stall or crash the game loop -- audio is a
    nice-to-have here, gameplay timing and scoring must never depend on it.
    Failures are logged (not raised) so they still show up in server logs."""
    task = asyncio.ensure_future(coro)
    task.add_done_callback(_log_sound_failure)


def build_simon_game_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.session
    if session is None:
        session = SimonSession(start_length=1, step_ms=state.progress.adaptive_step_ms())
        state.session = session

    sound = SoundBoard()
    lock = {"busy": True}  # pads ignore taps until the sequence finishes playing
    # False once the player leaves this screen. The sequence playback and the
    # pauses between rounds run as background tasks, so every step re-checks
    # this after each wait -- otherwise notes kept playing (and a finished
    # game could even jump to the summary) after going back to the menu.
    game = {"on_screen": True}

    def on_screen() -> bool:
        return game["on_screen"] and route_path(page.route) == "/simon"

    async def leave_game() -> None:
        game["on_screen"] = False
        await sound.stop_all()
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
        if not on_screen():
            return
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
        # the sound files load only once this screen appears; hold the first
        # note until they're ready so it isn't silent (instant on later rounds)
        if not await sound.wait_until_loaded(SOUND_LOAD_TIMEOUT_S):
            print("[audio] tones not loaded in time; playing without waiting", file=sys.stderr)
        await asyncio.sleep(0.6)
        for color_index in session.sequence:
            if not on_screen():
                return
            await flash_pad(color_index, session.step_ms)
            await asyncio.sleep(STEP_GAP_S)
        if not on_screen():
            return
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
        await leave_game()
        await page.push_route("/simon/summary")

    async def handle_pad_tap(index: int) -> None:
        if lock["busy"] or session.finished:
            return
        lock["busy"] = True
        await flash_pad(index, TAP_HIGHLIGHT_MS)
        if not on_screen():
            return
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
                if on_screen():
                    await finish_session()
                return
            status_label.value = "לא נורא, ננסה שוב פעם אחת!"
            page.update()
            await asyncio.sleep(INTER_ROUND_PAUSE_S)
            if on_screen():
                await play_sequence()
            return

        if len(player_input) == session.current_length:
            status_label.value = "מצוין!"
            page.update()
            session.record_round(True)
            save_progress()
            await asyncio.sleep(INTER_ROUND_PAUSE_S)
            if not on_screen():
                return
            if session.finished:
                await finish_session()
                return
            await play_sequence()
            return

        lock["busy"] = False

    async def exit_to_home(_: ft.ControlEvent) -> None:
        state.session = None
        await leave_game()
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
