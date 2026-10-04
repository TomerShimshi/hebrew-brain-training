import flet as ft

from simon.app_state import AppState
from simon.ui_helpers import ACCENT, GAME_THEMES, TEXT_SECONDARY, chip_button, rtl_text, soft_shadow
from simon.word_levels import LABELS as LEVEL_LABELS
from simon.word_levels import LEVELS

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


def _game_card(theme_key: str, title: str, subtitle: str, caption: str | None, on_click) -> ft.Container:
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
                        *([rtl_text(caption, size=13, color=theme["accent"])] if caption else []),
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


def _level_switch(page: ft.Page, state: AppState) -> ft.Row:
    """"רמת המילים: רגיל | מתקדם" -- the word level for the word games,
    remembered per profile. The selected level is filled in."""
    pills: dict[str, ft.Container] = {}

    def paint() -> None:
        for level, pill in pills.items():
            selected = level == state.word_level
            pill.bgcolor = ACCENT if selected else ft.Colors.with_opacity(0.10, ACCENT)
            pill.content.color = "#FFFFFF" if selected else ACCENT

    def pill(level: str) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            state.settings.word_level = level
            paint()
            page.update()

        pills[level] = ft.Container(
            content=rtl_text(LEVEL_LABELS[level], size=16, weight=ft.FontWeight.W_600),
            border_radius=20,
            padding=ft.Padding(18, 8, 18, 8),
            on_click=on_click,
            ink=True,
        )
        return pills[level]

    row = ft.Row(
        [rtl_text("רמת המילים:", size=15, color=TEXT_SECONDARY), *[pill(level) for level in LEVELS]],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
    )
    paint()
    return row


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

    def caption(last_time) -> str | None:
        # the public app keeps no history, so there's no "last time" to show
        return None if state.public else last_time(state)

    if state.public:
        top_card = rtl_text("ללא הרשמה · שום מידע לא נשמר", size=14, color=TEXT_SECONDARY)
        footer: list[ft.Control] = []
    else:
        top_card = _engagement_banner(state)
        footer = [ft.Container(height=20), chip_button("\U0001f4ca ההתקדמות שלי", go_progress, ACCENT)]

    return ft.View(
        route="/",
        controls=[
            ft.Column(
                [
                    ft.Text("Made by Tomer Shimshi", size=12, color=TEXT_SECONDARY),
                    rtl_text("משחקי אימון", size=40, weight=ft.FontWeight.BOLD),
                    ft.Container(height=4),
                    rtl_text("בחר משחק לתרגול", size=18, color=TEXT_SECONDARY),
                    ft.Container(height=20),
                    top_card,
                    ft.Container(height=16),
                    _level_switch(page, state),
                    ft.Container(height=16),
                    _game_card(
                        "simon",
                        "סיימון",
                        "משחק זיכרון צבעים ורצפים",
                        caption(_simon_caption),
                        start_simon,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "memory",
                        "זיכרון קלפים",
                        "מצא את הזוגות התואמים",
                        caption(_memory_caption),
                        start_memory,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "subword",
                        "בניית מילים",
                        "מצאו מילים בתוך מילה",
                        caption(_subword_caption),
                        start_subword,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "scramble",
                        "מילים מבולגנות",
                        "סדרו את האותיות למילה",
                        caption(_scramble_caption),
                        start_scramble,
                    ),
                    ft.Container(height=16),
                    _game_card(
                        "change_word",
                        "שינוי מילים",
                        "אותן אותיות, מילה חדשה",
                        caption(_change_word_caption),
                        start_change_word,
                    ),
                    *footer,
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
