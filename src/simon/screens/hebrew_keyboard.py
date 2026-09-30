from collections.abc import Callable

import flet as ft

from simon.ui_helpers import rtl_text

# The standard Israeli keyboard layout, each row written left-to-right as
# it appears on a physical keyboard -- so the layout looks familiar to
# anyone who has typed Hebrew on a computer or phone.
ROWS = [
    ["ק", "ר", "א", "ט", "ו", "ן", "ם", "פ"],
    ["ש", "ד", "ג", "כ", "ע", "י", "ח", "ל", "ך", "ף"],
    ["ז", "ס", "ב", "ה", "נ", "מ", "צ", "ת", "ץ"],
]
BACKSPACE_LABEL = "⌫"


def hebrew_keyboard(
    on_letter: Callable[[str], None],
    on_backspace: Callable[[], None],
    color: str,
) -> ft.Column:
    """A full on-screen Hebrew keyboard. Every letter is always available,
    so the player has to recall a word rather than pick from a given set
    of letters."""

    def key(label: str, on_click, width: int = 34, bgcolor: str = "#FFFFFF", text_color: str | None = None):
        return ft.Container(
            content=rtl_text(label, size=22, weight=ft.FontWeight.W_600, color=text_color or color),
            bgcolor=bgcolor,
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, color)),
            border_radius=8,
            width=width,
            height=50,
            alignment=ft.Alignment(0, 0),
            on_click=on_click,
            ink=True,
        )

    def letter_key(letter: str) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            on_letter(letter)

        return key(letter, on_click)

    async def backspace_click(_: ft.ControlEvent) -> None:
        on_backspace()

    def row(controls: list[ft.Control]) -> ft.Row:
        # the page is right-to-left, which would mirror each row; laying
        # the row out left-to-right keeps keys where a real keyboard has them
        return ft.Row(controls, alignment=ft.MainAxisAlignment.CENTER, spacing=4, rtl=False)

    return ft.Column(
        [
            row([letter_key(letter) for letter in ROWS[0]]),
            row([letter_key(letter) for letter in ROWS[1]]),
            row(
                [letter_key(letter) for letter in ROWS[2]]
                + [key(BACKSPACE_LABEL, backspace_click, width=52, bgcolor=color, text_color="#FFFFFF")]
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
    )
