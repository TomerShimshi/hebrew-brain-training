import flet as ft

BACKGROUND = "#F4F6FB"
TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#5B6472"
ACCENT = ft.Colors.BLUE_600

# Each game gets its own identity (accent color + soft tint for
# backgrounds/chips + an emoji icon) so the games are instantly
# distinguishable at a glance on the home hub and inside each game's own
# screens -- useful recognition support independent of reading the title.
GAME_THEMES = {
    "simon": {"accent": "#3B5BDB", "light": "#E7EBFC", "icon": "\U0001f3ae"},
    "memory": {"accent": "#0F9D74", "light": "#E1F6EE", "icon": "\U0001f0cf"},
    "subword": {"accent": "#E8590C", "light": "#FDECE1", "icon": "\U0001f524"},
    "scramble": {"accent": "#7048E8", "light": "#EFEAFD", "icon": "\U0001f500"},
}

# Unlit / lit pairs per pad -- the lit shade is a brightened version of the
# same hue so the flash reads clearly even to a viewer with reduced contrast
# sensitivity, without changing which color is which.
PAD_COLORS = {
    "red": "#C62828",
    "blue": "#1565C0",
    "green": "#2E7D32",
    "yellow": "#F9A825",
}
PAD_COLORS_LIT = {
    "red": "#FF6E63",
    "blue": "#66A3FF",
    "green": "#66BB6A",
    "yellow": "#FFE066",
}


def soft_shadow(color: str = "#1A1A1A", opacity: float = 0.12, blur: float = 16) -> ft.BoxShadow:
    return ft.BoxShadow(
        blur_radius=blur,
        spread_radius=0,
        color=ft.Colors.with_opacity(opacity, color),
        offset=ft.Offset(0, 4),
    )


def rtl_text(
    value: str,
    size: int = 20,
    weight: ft.FontWeight | None = None,
    color: str | None = None,
) -> ft.Text:
    return ft.Text(
        value,
        rtl=True,
        size=size,
        weight=weight,
        color=color or TEXT_PRIMARY,
        text_align=ft.TextAlign.CENTER,
    )


def primary_button(label: str, on_click, color: str | None = None) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        content=rtl_text(label, size=26, color="#FFFFFF"),
        on_click=on_click,
        bgcolor=color or ACCENT,
        height=76,
        width=280,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=18), elevation=4),
    )


def bar_chart(values: list[float], color: str, max_bar_height: float = 90, bar_width: float = 22) -> ft.Container:
    """A minimal bottom-aligned bar chart -- no charting library, just
    height-scaled Containers, to match the rest of the app's plain-Flet
    visual style and avoid adding another versioned extension package
    dependency (flet-audio and flet-web both caused real friction earlier
    in this project). `values` is oldest-to-newest, left-to-right within
    the row regardless of page RTL (each bar has no inherent reading
    direction, so this reads fine either way)."""
    peak = max(values) if values else 0
    bars = [
        ft.Container(
            width=bar_width,
            height=max(6, (v / peak) * max_bar_height) if peak else 6,
            bgcolor=color,
            border_radius=6,
        )
        for v in values
    ]
    return ft.Container(
        content=ft.Row(
            bars,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=6,
        ),
        height=max_bar_height,
    )


def chip_button(label: str, on_click, color: str = ACCENT) -> ft.TextButton:
    """A small pill-shaped secondary action (clear/undo/hint-style buttons)
    tinted with the current game's accent color, instead of a plain
    unstyled text link -- keeps secondary actions visually tied to the
    game's identity without competing with the primary button."""
    return ft.TextButton(
        content=rtl_text(label, size=15, weight=ft.FontWeight.W_600, color=color),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.10, color),
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.Padding(16, 10, 16, 10),
        ),
    )
