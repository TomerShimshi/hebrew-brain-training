from collections.abc import Callable

import flet as ft

from simon.ui_helpers import rtl_text

# The 22 letters in alphabetical order, 6 to a row: alphabetical order is
# easy to scan for someone who doesn't type much, and 4 rows of 6 leaves
# room for big keys. There are no final-form keys (ך ם ן ף ץ): the app
# turns a word's last letter into its final form by itself, so typing מ at
# the end of שלום shows ם.
ALPHABET = list("אבגדהוזחטיכלמנסעפצקרשת")
KEYS_PER_ROW = 6
KEY_SPACING = 6
KEY_HEIGHT = 58
BACKSPACE_LABEL = "⌫"


def hebrew_keyboard(
    on_letter: Callable[[str], None],
    on_backspace: Callable[[], None],
    color: str,
    width: float,
) -> ft.Container:
    """A full on-screen Hebrew keyboard with large keys, sized to the width
    it's given. Every letter is always available, so the player has to
    recall a word rather than pick from a given set of letters. Keys share
    each row's width equally; the shorter last row (4 letters + backspace)
    is centred with padding so all keys are the same size."""

    def key(label: str, on_click, bgcolor: str, text_color: str) -> ft.Container:
        return ft.Container(
            content=rtl_text(label, size=28, weight=ft.FontWeight.BOLD, color=text_color),
            bgcolor=bgcolor,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.4, color)),
            border_radius=12,
            height=KEY_HEIGHT,
            expand=2,
            alignment=ft.Alignment(0, 0),
            on_click=on_click,
            ink=True,
        )

    def letter_key(letter: str) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            on_letter(letter)

        return key(letter, on_click, "#FFFFFF", color)

    async def backspace_click(_: ft.ControlEvent) -> None:
        on_backspace()

    def row(controls: list[ft.Control]) -> ft.Row:
        padding = KEYS_PER_ROW - len(controls)
        if padding:
            # half the missing width on each side keeps every key the same size
            controls = [ft.Container(expand=padding), *controls, ft.Container(expand=padding)]
        return ft.Row(controls, spacing=KEY_SPACING)

    keys: list[ft.Control] = [letter_key(letter) for letter in ALPHABET]
    keys.append(key(BACKSPACE_LABEL, backspace_click, color, "#FFFFFF"))
    rows = [keys[i:i + KEYS_PER_ROW] for i in range(0, len(keys), KEYS_PER_ROW)]
    return ft.Container(content=ft.Column([row(r) for r in rows], spacing=KEY_SPACING), width=width)
