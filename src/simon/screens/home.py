import flet as ft

from simon.app_state import AppState
from simon.choice_games import CHOICE_GAMES, ChoiceGame
from simon.ui_helpers import ACCENT, GAME_THEMES, TEXT_SECONDARY, chip_button, rtl_text, soft_shadow
from simon.word_levels import LABELS as LEVEL_LABELS
from simon.word_levels import LEVELS

SOURCE_URL = "https://github.com/TomerShimshi/hebrew-brain-training"
DOT_FILLED = ACCENT
DOT_EMPTY = "#E3E7F0"


NOT_PLAYED = "עדיין לא שיחקת"
TILE_WIDTH = 159
TILE_SPACING = 12  # two tiles and the gap between them fill the 330px column


def _last_time(last: dict | None, text) -> str:
    return NOT_PLAYED if last is None else text(last)


def _simon_caption(state: AppState) -> str:
    return _last_time(state.progress.last_session(), lambda last: f"רצף {last['best_length']}")


def _memory_caption(state: AppState) -> str:
    return _last_time(state.memory_progress.last_session(), lambda last: f"{last['moves']} צעדים")


def _subword_caption(state: AppState) -> str:
    return _last_time(state.subword_progress.last_session(), lambda last: f"{last['words_found_count']} מילים")


def _scramble_caption(state: AppState) -> str:
    return _last_time(state.scramble_progress.last_session(), lambda last: f"{last['words_solved_count']} מילים")


def _change_word_caption(state: AppState) -> str:
    return _last_time(state.change_word_progress.last_session(), lambda last: f"{last['changes_solved']} מילים")


def _choice_caption(game: ChoiceGame):
    def caption(state: AppState) -> str:
        return _last_time(
            state.choice_progress[game.key].last_session(),
            lambda last: f"{last['first_try_correct']} מתוך {last['answered']}",
        )

    return caption


def _game_tile(game_key: str, theme_key: str, title: str, caption: str | None, on_click) -> ft.Container:
    """A square-ish tile: the game's icon in a round bubble, its name, and
    (family app only) a short line about last time. The whole tile is the
    button."""
    theme = GAME_THEMES[theme_key]
    icon_bubble = ft.Container(
        content=rtl_text(theme["icon"], size=32),
        width=60,
        height=60,
        border_radius=30,
        bgcolor=theme["light"],
        alignment=ft.Alignment(0, 0),
    )
    caption_line = ft.Text(
        caption,
        rtl=True,
        size=13,
        color=theme["accent"],
        text_align=ft.TextAlign.CENTER,
        data=f"caption:{game_key}",
    )
    return ft.Container(
        content=ft.Column(
            [icon_bubble, rtl_text(title, size=19, weight=ft.FontWeight.BOLD), *([caption_line] if caption else [])],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor="#FFFFFF",
        border=ft.Border.all(2, theme["light"]),
        border_radius=20,
        padding=ft.Padding(8, 14, 8, 14),
        width=TILE_WIDTH,
        height=150,
        shadow=soft_shadow(),
        on_click=on_click,
        ink=True,
        data=f"game:{game_key}",
    )


def _tile_grid(tiles: list[ft.Container]) -> list[ft.Row]:
    return [
        ft.Row(tiles[i : i + 2], spacing=TILE_SPACING, alignment=ft.MainAxisAlignment.CENTER, data="tile-row")
        for i in range(0, len(tiles), 2)
    ]


def _section(key: str, title: str, controls: list[ft.Control]) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [rtl_text(title, size=21, weight=ft.FontWeight.BOLD), *controls],
            spacing=TILE_SPACING,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        data=f"section:{key}",
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
                ft.Container(height=8),
                _week_dots(state),
                ft.Container(height=4),
                rtl_text(f"סה״כ ימי תרגול: {total_days}", size=13, color=TEXT_SECONDARY),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=14,
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
        data="level-switch",
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

    def start_choice(game: ChoiceGame):
        async def start(_: ft.ControlEvent) -> None:
            state.choice_sessions[game.key] = None  # let the game build a fresh session
            await page.push_route(game.route)

        return start

    async def go_progress(_: ft.ControlEvent) -> None:
        await page.push_route("/progress")

    def caption(last_time) -> str | None:
        # the public app keeps no history, so there's no "last time" to show
        return None if state.public else last_time(state)

    if state.public:
        top_card = rtl_text("ללא הרשמה · שום מידע אישי לא נשמר", size=14, color=TEXT_SECONDARY)
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
                    rtl_text("משחקי אימון", size=34, weight=ft.FontWeight.BOLD),
                    rtl_text("בחר משחק לתרגול", size=16, color=TEXT_SECONDARY),
                    ft.Container(height=12),
                    top_card,
                    ft.Container(height=20),
                    _section(
                        "memory",
                        "\U0001f9e0 משחקי זיכרון",
                        _tile_grid(
                            [
                                _game_tile("simon", "simon", "סיימון", caption(_simon_caption), start_simon),
                                _game_tile("memory", "memory", "זיכרון קלפים", caption(_memory_caption), start_memory),
                            ]
                        ),
                    ),
                    ft.Container(height=24),
                    _section(
                        "words",
                        "\U0001f524 משחקי מילים",
                        [
                            _level_switch(page, state),
                            *_tile_grid(
                                [
                                    _game_tile(
                                        "subword", "subword", "בניית מילים", caption(_subword_caption), start_subword
                                    ),
                                    _game_tile(
                                        "scramble", "scramble", "מילים מבולגנות", caption(_scramble_caption), start_scramble
                                    ),
                                    _game_tile(
                                        "change_word",
                                        "change_word",
                                        "שינוי מילים",
                                        caption(_change_word_caption),
                                        start_change_word,
                                    ),
                                    *[
                                        _game_tile(
                                            game.key,
                                            game.theme_key,
                                            game.title,
                                            caption(_choice_caption(game)),
                                            start_choice(game),
                                        )
                                        for game in CHOICE_GAMES.values()
                                    ],
                                ]
                            ),
                        ],
                    ),
                    *footer,
                    ft.Container(height=16),
                    # The code is AGPL-3.0, which asks that users of the app
                    # (including over the web) can get its source -- hence
                    # the link. Some word-game clues are adapted from
                    # ויקימילון definitions (CC BY-SA), which needs credit.
                    rtl_text("קוד פתוח ברישיון AGPL-3.0:", size=11, color=TEXT_SECONDARY),
                    # the URL is left-to-right, on its own line so mixing it
                    # with Hebrew doesn't scramble the word order
                    ft.Text(
                        spans=[
                            ft.TextSpan(
                                SOURCE_URL.removeprefix("https://"),
                                url=SOURCE_URL,
                                style=ft.TextStyle(color=ACCENT, decoration=ft.TextDecoration.UNDERLINE),
                            )
                        ],
                        size=11,
                        rtl=False,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    rtl_text("חלק מההגדרות מבוססות על ויקימילון (CC BY-SA)", size=11, color=TEXT_SECONDARY),
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
