from collections.abc import Callable

import flet as ft

from simon.letter_puzzle import GuessResult, LetterPuzzle
from simon.ui_helpers import rtl_text, soft_shadow

SLOT_EMPTY_COLOR = "#FFFFFF"
SLOT_SOLVED_COLOR = "#D3F9D8"


class LetterBoard:
    """The answer slots plus tappable letter tiles for one LetterPuzzle,
    shared by the letter-tile games. Tapping a tile places its letter in
    the next slot, and the attempt is checked the moment the last slot
    fills (the answer's length is visible as slots, so there's no need
    for a separate "check" button). `on_tap` receives the check result so
    the screen can show feedback and save progress.
    """

    def __init__(
        self,
        page: ft.Page,
        accent: str,
        light: str,
        used_tile_color: str,
        on_tap: Callable[[GuessResult], None],
    ) -> None:
        self._page = page
        self._accent = accent
        self._light = light
        self._used_tile_color = used_tile_color
        self._on_tap = on_tap
        self._tiles: list[ft.Container] = []
        self._slots: list[ft.Container] = []
        self.puzzle: LetterPuzzle | None = None
        self._slot_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6, wrap=True, run_spacing=6)
        self._tile_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10, wrap=True, run_spacing=10)
        self.control = ft.Column(
            [
                ft.Container(content=self._slot_row, padding=ft.Padding(0, 12, 0, 4)),
                ft.Container(content=self._tile_row, padding=16),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )

    def set_puzzle(self, puzzle: LetterPuzzle) -> None:
        self.puzzle = puzzle
        self._tiles = [self._build_tile(i) for i in range(len(puzzle.tiles))]
        self._slots = [self._build_slot() for _ in puzzle.tiles]
        self._tile_row.controls = self._tiles
        self._slot_row.controls = self._slots
        self.render()

    def render(self) -> None:
        puzzle = self.puzzle
        for i, tile in enumerate(self._tiles):
            tile.bgcolor = self._used_tile_color if i in puzzle.current_attempt else self._accent
        for slot, letter in zip(self._slots, puzzle.slot_letters()):
            slot.content.value = letter
            if puzzle.solved:
                slot.bgcolor = SLOT_SOLVED_COLOR
            elif puzzle.revealed:
                slot.bgcolor = self._light
            else:
                slot.bgcolor = SLOT_EMPTY_COLOR

    def _build_tile(self, index: int) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            self.puzzle.tap_tile(index)
            result = self.puzzle.check_attempt()
            self.render()
            self._on_tap(result)
            self._page.update()

        return ft.Container(
            content=rtl_text(self.puzzle.tiles[index], size=30, color="#FFFFFF"),
            bgcolor=self._accent,
            border_radius=14,
            width=60,
            height=60,
            alignment=ft.Alignment(0, 0),
            on_click=on_click,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            shadow=soft_shadow(self._accent, opacity=0.3, blur=8),
        )

    def _build_slot(self) -> ft.Container:
        return ft.Container(
            content=rtl_text("", size=28, weight=ft.FontWeight.BOLD),
            bgcolor=SLOT_EMPTY_COLOR,
            border=ft.Border.all(2, self._accent),
            border_radius=10,
            width=48,
            height=56,
            alignment=ft.Alignment(0, 0),
        )
