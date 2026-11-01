"""The family app's view of the public app's anonymous usage counts (see
usage_stats): visits, different visitors and how often they come, visits
that actually played, and games started."""

import flet as ft

from simon.app_state import AppState
from simon.choice_games import CHOICE_GAMES
from simon.ui_helpers import ACCENT, GAME_THEMES, TEXT_SECONDARY, bar_chart, chip_button, rtl_text, soft_shadow
from simon.usage_stats import PLAYED, VISIT, game_counts, get_usage_stats, visitor_days

DAYS = 30
CHART_DAYS = 14
# "came at least N days" milestones, and from which day of visiting a
# visitor is a regular (before that, from day 2: occasional)
MILESTONES = (2, 5, 10)
REGULAR_FROM = 5

GAME_TITLES = {
    "simon": "סיימון",
    "memory": "זיכרון קלפים",
    "subword": "בניית מילים",
    "scramble": "מילים מבולגנות",
    "change_word": "שינוי מילים",
    **{game.key: game.title for game in CHOICE_GAMES.values()},
}


def _card(title: str, body: list[ft.Control]) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [rtl_text(title, size=20, weight=ft.FontWeight.BOLD), ft.Container(height=6), *body],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        bgcolor="#FFFFFF",
        border_radius=20,
        padding=18,
        width=330,
        shadow=soft_shadow(),
    )


def _visitors(counts: dict[str, int]) -> int:
    return sum(visitor_days(counts).values())


def _all_time(totals: dict[str, int]) -> ft.Container:
    # each browser counts once for each day of visiting it reaches, so the
    # day-N count is how many browsers came at least N days
    reached = visitor_days(totals)
    return _card(
        "מאז ההתחלה",
        [
            rtl_text(f"מבקרים מאז ההתחלה: {reached.get(1, 0)}", size=18, weight=ft.FontWeight.W_600, color=ACCENT),
            *[rtl_text(f"באו לפחות {n} ימים: {reached.get(n, 0)}", size=16) for n in MILESTONES],
            rtl_text("כל מכשיר נספר כמבקר אחד", size=12, color=TEXT_SECONDARY),
        ],
    )


def _report(days: list, totals: dict[str, int] | None) -> list[ft.Control]:
    visits = sum(c.get(VISIT, 0) for _d, c in days)
    new = occasional = regular = 0
    for _day, counts in days:
        for n, browsers in visitor_days(counts).items():
            if n == 1:
                new += browsers
            elif n < REGULAR_FROM:
                occasional += browsers
            else:
                regular += browsers
    played = sum(c.get(PLAYED, 0) for _d, c in days)
    games: dict[str, int] = {}
    for _day, counts in days:
        for key, n in game_counts(counts).items():
            games[key] = games.get(key, 0) + n

    recent = [c.get(PLAYED, 0) for _d, c in reversed(days[:CHART_DAYS])]  # oldest -> newest
    totals_card = _card(
        f"{DAYS} הימים האחרונים",
        [
            rtl_text(f"ביקורים: {visits}", size=18),
            rtl_text(f"מבקרים: {new + occasional + regular}", size=18),
            rtl_text(f"חדשים {new} · מזדמנים {occasional} · קבועים {regular}", size=16),
            rtl_text("כל מכשיר נספר פעם אחת ביום", size=12, color=TEXT_SECONDARY),
            rtl_text(
                f"מזדמנים: 2 עד {REGULAR_FROM - 1} ימים · קבועים: {REGULAR_FROM} ימים ומעלה",
                size=12,
                color=TEXT_SECONDARY,
            ),
            rtl_text(f"ביקורים ששיחקו: {played}", size=18, weight=ft.FontWeight.W_600, color=ACCENT),
            ft.Container(height=10),
            bar_chart(recent, ACCENT, bar_width=14) if any(recent) else ft.Container(),
            rtl_text(f"ביקורים ששיחקו בכל יום ({CHART_DAYS} הימים האחרונים)", size=12, color=TEXT_SECONDARY)
            if any(recent)
            else ft.Container(),
        ],
    )
    game_rows = [
        rtl_text(f"{GAME_THEMES.get(key, {}).get('icon', '')} {GAME_TITLES.get(key, key)}: {n}", size=17)
        for key, n in sorted(games.items(), key=lambda kv: -kv[1])
    ]
    games_card = _card("משחקים שהתחילו", game_rows or [rtl_text("עדיין אין", size=15, color=TEXT_SECONDARY)])
    day_rows = [
        rtl_text(
            f"{day.day}.{day.month} · {c.get(VISIT, 0)} ביקורים · {_visitors(c)} מבקרים · {c.get(PLAYED, 0)} שיחקו",
            size=15,
        )
        for day, c in days
        if c.get(VISIT, 0) or c.get(PLAYED, 0)
    ]
    days_card = _card("לפי יום", day_rows or [rtl_text("עדיין אין ביקורים", size=15, color=TEXT_SECONDARY)])
    all_time = [_all_time(totals), ft.Container(height=16)] if totals is not None else []
    return [*all_time, totals_card, ft.Container(height=16), games_card, ft.Container(height=16), days_card]


def build_usage_view(page: ft.Page, state: AppState) -> ft.View:
    async def go_back(_: ft.ControlEvent) -> None:
        await page.push_route("/progress")

    stats = get_usage_stats()
    if stats is None:
        body = [rtl_text("מונה השימוש עוד לא הוגדר (ראו README)", size=16, color=TEXT_SECONDARY)]
    else:
        days = stats.daily_counts(days=DAYS)
        body = _report(days, stats.totals()) if days else [
            rtl_text("לא הצלחנו לקרוא את הנתונים כרגע, נסו שוב מאוחר יותר", size=16, color=TEXT_SECONDARY)
        ]

    return ft.View(
        route="/usage",
        controls=[
            ft.Column(
                [
                    ft.Row([chip_button("חזרה", go_back, ACCENT)], alignment=ft.MainAxisAlignment.CENTER),
                    rtl_text("שימוש באפליקציה הציבורית", size=28, weight=ft.FontWeight.BOLD),
                    rtl_text("ספירה אנונימית בלבד -- בלי שמות ובלי פרטים אישיים", size=13, color=TEXT_SECONDARY),
                    ft.Container(height=20),
                    *body,
                    ft.Container(height=24),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
