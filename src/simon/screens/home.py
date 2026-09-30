import flet as ft

from simon.app_state import AppState
from simon.ui_helpers import ACCENT, GAME_THEMES, TEXT_SECONDARY, chip_button, rtl_text, soft_shadow

DOT_FILLED = ACCENT
DOT_EMPTY = "#E3E7F0"


def _simon_caption(state: AppState) -> str:
    last = state.progress.last_session()
    if last is None:
        return "עדיין לא שיחקת"
    return f"בפעם הקודמת: רצף באורך {last['best_length']}"


def _memory_caption(state: AppState) -> str:
    last = state.memory_progress.last_session()
    if last is None:
        return "עדיין לא שיחקת"
    return f"בפעם הקודמת: {last['moves']} צעדים"


def _subword_caption(state: AppState) -> str:
    last = state.subword_progress.last_session()
    if last is None:
        return "עדיין לא שיחקת"
    return f"בפעם הקודמת: {last['words_found_count']} מילים"


def _scramble_caption(state: AppState) -> str:
    last = state.scramble_progress.last_session()
    if last is None:
        return "עדיין לא שיחקת"
    return f"בפעם הקודמת: {last['words_solved_count']} מילים ({last['category']})"


def _change_word_caption(state: AppState) -> str:
    last = state.change_word_progress.last_session()
    if last is None:
        return "עדיין לא שיחקת"
    return f"בפעם הקודמת: שינית {last['changes_solved']} מילים"


def _game_card(theme_key: str, title: str, subtitle: str, caption: str, on_click) -> ft.Container:
    theme = GAME_THEMES[theme_key]
    icon_bubble = ft.Container(
        content=rtl_text(theme["icon"], size=34),
        width=64,
        height=64,
        border_radius=32,
        bgcolor=theme["light"],
        alignment=ft.Alignment(0, 0),
    )
    return ft.Container(
        content=ft.Row(
            [
                icon_bubble,
                ft.Column(
                    [
                        rtl_text(title, size=22, weight=ft.FontWeight.BOLD),
                        rtl_text(subtitle, size=14, color=TEXT_SECONDARY),
                        rtl_text(caption, size=13, color=theme["accent"]),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor="#FFFFFF",
        border=ft.Border.all(2, theme["light"]),
        border_radius=20,
        padding=18,
        width=330,
        shadow=soft_shadow(),
        on_click=on_click,
        ink=True,
    )


def _week_dots(state: AppState) -> ft.Row:
    days = state.engagement.last_n_days(7)
    return ft.Row(
        [
            ft.Container(
                width=16,
                height=16,
                border_radius=8,
                bgcolor=DOT_FILLED if visited else DOT_EMPTY,
            )
            for _day, visited in days
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
    )


def _engagement_banner(state: AppState) -> ft.Container:
    total_days = state.engagement.total_days_played()
    streak = state.engagement.current_streak()

    if streak >= 2:
        headline = f"\U0001f525 {streak} ימים ברצף!"
    elif total_days <= 1:
        headline = "ברוכים הבאים!"
    else:
        headline = "כיף לראות אותך היום!"

    return ft.Container(
        content=ft.Column(
            [
                rtl_text(headline, size=20, weight=ft.FontWeight.BOLD, color=ACCENT),
                ft.Container(height=10),
                _week_dots(state),
                ft.Container(height=6),
                rtl_text(f"סה״כ ימי תרגול: {total_days}", size=13, color=TEXT_SECONDARY),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=18,
        width=330,
        shadow=soft_shadow(),
    )


def build_home_view(page: ft.Page, state: AppState) -> ft.View:
    async def start_simon(_: ft.ControlEvent) -> None:
        state.session = None  # let /simon build a fresh session starting at length 1
        await page.push_route("/simon")

    async def start_memory(_: ft.ControlEvent) -> None:
        state.memory_session = None  # let /memory build a fresh grid
        await page.push_route("/memory")

    async def start_subword(_: ft.ControlEvent) -> None:
        state.subword_session = None  # let /subword build a fresh session
        await page.push_route("/subword")

    async def start_scramble(_: ft.ControlEvent) -> None:
        state.scramble_session = None  # /scramble opens on the category picker
        await page.push_route("/scramble")

    async def start_change_word(_: ft.ControlEvent) -> None:
        state.change_word_session = None  # let /change build a fresh session
        await page.push_route("/change")

    async def go_progress(_: ft.ControlEvent) -> None:
        await page.push_route("/progress")

    return ft.View(
        route="/",
        controls=[
            ft.Column(
                [
                    rtl_text("משחקי אימון", size=40, weight=ft.FontWeight.BOLD),
                    ft.Container(height=4),
                    rtl_text("בחר משחק לתרגול", size=18, color=TEXT_SECONDARY),
                    ft.Container(height=20),
                    _engagement_banner(state),
                    ft.Container(height=24),
                    _game_card(
                        "simon",
                        "סיימון",
                        "משחק זיכרון צבעים ורצפים",
                        _simon_caption(state),
                        start_simon,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "memory",
                        "זיכרון קלפים",
                        "מצא את הזוגות התואמים",
                        _memory_caption(state),
                        start_memory,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "subword",
                        "בניית מילים",
                        "מצאו מילים בתוך מילה",
                        _subword_caption(state),
                        start_subword,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "scramble",
                        "מילים מבולגנות",
                        "סדרו את האותיות למילה",
                        _scramble_caption(state),
                        start_scramble,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "change_word",
                        "שינוי מילים",
                        "אותן אותיות, מילה חדשה",
                        _change_word_caption(state),
                        start_change_word,
                    ),
                    ft.Container(height=20),
                    chip_button("\U0001f4ca ההתקדמות שלי", go_progress, ACCENT),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
