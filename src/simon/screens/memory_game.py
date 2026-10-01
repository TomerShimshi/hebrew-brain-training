import asyncio
import math

import flet as ft

from simon.app_state import AppState
from simon.memory_session import DEFAULT_PAIR_COUNT, MemoryGameSession
from simon.ui_helpers import GAME_THEMES, chip_button, game_header, rtl_text, soft_shadow

THEME = GAME_THEMES["memory"]

MISMATCH_PAUSE_S = 0.9
MATCH_PAUSE_S = 0.6
FINISH_PAUSE_S = 1.0
FACE_DOWN_COLOR = THEME["accent"]
FACE_UP_COLOR = "#FFFFFF"
MATCHED_COLOR = "#BFEBD9"


def _grid_columns(total_cards: int) -> int:
    return min(4, max(2, math.ceil(math.sqrt(total_cards))))


def build_memory_game_view(page: ft.Page, state: AppState) -> ft.View:
    session = state.memory_session
    if session is None:
        session = MemoryGameSession(pair_count=DEFAULT_PAIR_COUNT)
        state.memory_session = session

    lock = {"busy": False}

    status_label = rtl_text("מצא את הזוגות התואמים", size=22, weight=ft.FontWeight.BOLD)
    moves_label = rtl_text("צעדים: 0", size=16)
    cards: dict[int, ft.Container] = {}

    def render_card(index: int) -> None:
        card = cards[index]
        if index in session.matched:
            card.bgcolor = MATCHED_COLOR
            card.content.value = session.cards[index]
        elif index in session.revealed:
            card.bgcolor = FACE_UP_COLOR
            card.content.value = session.cards[index]
        else:
            card.bgcolor = FACE_DOWN_COLOR
            card.content.value = ""

    def render_all() -> None:
        for i in cards:
            render_card(i)
        moves_label.value = f"צעדים: {session.moves}"

    def save_progress() -> None:
        state.memory_progress.save_session(
            session.log_id,
            pair_count=session.pair_count,
            moves=session.moves,
            mismatches=session.mismatches,
            completed=session.is_complete,
        )

    async def finish_session() -> None:
        save_progress()
        await page.push_route("/memory/summary")

    async def handle_card_tap(index: int) -> None:
        if lock["busy"]:
            return

        just_completed_pair = session.reveal(index)
        render_card(index)
        page.update()
        if not just_completed_pair:
            return

        lock["busy"] = True
        matched = session.resolve()
        if matched:
            save_progress()
        await asyncio.sleep(MATCH_PAUSE_S if matched else MISMATCH_PAUSE_S)
        render_all()
        page.update()

        if session.is_complete:
            status_label.value = "כל הכבוד, מצאת את כל הזוגות!"
            page.update()
            await asyncio.sleep(FINISH_PAUSE_S)
            await finish_session()
            return

        lock["busy"] = False

    def build_card(index: int) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            await handle_card_tap(index)

        card = ft.Container(
            content=rtl_text("", size=32),
            bgcolor=FACE_DOWN_COLOR,
            border_radius=14,
            alignment=ft.Alignment(0, 0),
            on_click=on_click,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            shadow=soft_shadow(FACE_DOWN_COLOR, opacity=0.25, blur=8),
        )
        cards[index] = card
        return card

    grid = ft.GridView(
        controls=[build_card(i) for i in range(len(session.cards))],
        runs_count=_grid_columns(len(session.cards)),
        spacing=12,
        run_spacing=12,
        expand=True,
    )

    async def exit_to_home(_: ft.ControlEvent) -> None:
        state.memory_session = None
        await page.push_route("/")

    return ft.View(
        route="/memory",
        controls=[
            ft.Column(
                [
                    game_header(f"זיכרון קלפים {THEME['icon']}", THEME["accent"], "חזרה לתפריט", exit_to_home),
                    status_label,
                    moves_label,
                    ft.Container(content=grid, expand=True, padding=16),
                ],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
