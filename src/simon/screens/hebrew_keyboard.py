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
KEY_SPACING = 4


def hebrew_keyboard(
    on_letter: Callable[[str], None],
    on_backspace: Callable[[], None],
    color: str,
    width: float,
) -> ft.Container:
    """A full on-screen Hebrew keyboard. Every letter is always available,
    so the player has to recall a word rather than pick from a given set
    of letters.

    Keys share each row's width equally (every row is 10 key-widths: the
    8-key top row is padded by one key on each side, the backspace fills
    the bottom row's 10th slot), so the keyboard always fits the screen
    it's given instead of overflowing a narrow phone."""

    def key(label: str, on_click, bgcolor: str = "#FFFFFF", text_color: str | None = None) -> ft.Container:
        return ft.Container(
            content=rtl_text(label, size=20, weight=ft.FontWeight.W_600, color=text_color or color),
            bgcolor=bgcolor,
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, color)),
            border_radius=8,
            height=48,
            expand=2,
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

    def key_gap() -> ft.Container:
        return ft.Container(expand=2)

    def row(controls: list[ft.Control]) -> ft.Row:
        # The page is right-to-left, which lays a row out starting from the
        # right; reversing puts each key where a real keyboard has it
        # (ק at the top-left).
        return ft.Row(list(reversed(controls)), spacing=KEY_SPACING)

    return ft.Container(
        content=ft.Column(
            [
                row([key_gap(), *[letter_key(letter) for letter in ROWS[0]], key_gap()]),
                row([letter_key(letter) for letter in ROWS[1]]),
                row(
                    [letter_key(letter) for letter in ROWS[2]]
                    + [key(BACKSPACE_LABEL, backspace_click, bgcolor=color, text_color="#FFFFFF")]
                ),
            ],
            spacing=6,
        ),
        width=width,
    )
