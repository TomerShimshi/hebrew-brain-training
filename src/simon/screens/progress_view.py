import flet as ft

from simon.app_state import AppState
from simon.ui_helpers import ACCENT, GAME_THEMES, TEXT_SECONDARY, bar_chart, chip_button, rtl_text, soft_shadow

SESSIONS_SHOWN = 10


def _trend_message(values: list[float], higher_is_better: bool) -> str:
    """Always gentle, never negative -- an apparent decline is framed as
    encouragement to keep practicing, not as a setback, matching the app's
    non-punitive design throughout."""
    if len(values) < 2:
        return "המשיכו לתרגל כדי לראות כאן התקדמות!"
    improved = (values[-1] > values[0]) if higher_is_better else (values[-1] < values[0])
    return "רואים שיפור יפה!" if improved else "כל תרגול עוזר -- המשיכו כך!"


def _game_trend_card(
    theme_key: str,
    title: str,
    sessions: list[dict],
    value_key: str,
    value_label: str,
    higher_is_better: bool = True,
) -> ft.Container:
    theme = GAME_THEMES[theme_key]

    if not sessions:
        body = rtl_text(
            "עדיין אין נתונים -- שחקו כדי להתחיל לראות כאן התקדמות",
            size=14,
            color=TEXT_SECONDARY,
        )
    else:
        values = [s[value_key] for s in sessions]
        body = ft.Column(
            [
                bar_chart(values, theme["accent"]),
                ft.Container(height=8),
                rtl_text(value_label, size=12, color=TEXT_SECONDARY),
                ft.Container(height=6),
                rtl_text(
                    _trend_message(values, higher_is_better),
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=theme["accent"],
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    return ft.Container(
        content=ft.Column(
            [
                rtl_text(f"{title} {theme['icon']}", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                body,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#FFFFFF",
        border=ft.Border.all(2, theme["light"]),
        border_radius=20,
        padding=18,
        width=330,
        shadow=soft_shadow(),
    )


def build_progress_view(page: ft.Page, state: AppState) -> ft.View:
    simon_sessions = state.progress.recent_sessions(n=SESSIONS_SHOWN)
    memory_sessions = state.memory_progress.recent_sessions(n=SESSIONS_SHOWN)
    subword_sessions = state.subword_progress.recent_sessions(n=SESSIONS_SHOWN)
    scramble_sessions = state.scramble_progress.recent_sessions(n=SESSIONS_SHOWN)

    async def go_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    return ft.View(
        route="/progress",
        controls=[
            ft.Column(
                [
                    ft.Row(
                        [chip_button("חזרה לתפריט", go_home, ACCENT)],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    rtl_text("\U0001f4ca ההתקדמות שלי", size=32, weight=ft.FontWeight.BOLD),
                    ft.Container(height=4),
                    rtl_text(f"{SESSIONS_SHOWN} המשחקים האחרונים בכל תרגיל", size=14, color=TEXT_SECONDARY),
                    ft.Container(height=24),
                    _game_trend_card(
                        "simon",
                        "סיימון",
                        simon_sessions,
                        "best_length",
                        "אורך הרצף בכל משחק (גבוה יותר = טוב יותר)",
                        higher_is_better=True,
                    ),
                    ft.Container(height=16),
                    _game_trend_card(
                        "memory",
                        "זיכרון קלפים",
                        memory_sessions,
                        "moves",
                        "מספר הצעדים בכל משחק (נמוך יותר = טוב יותר)",
                        higher_is_better=False,
                    ),
                    ft.Container(height=16),
                    _game_trend_card(
                        "subword",
                        "בניית מילים",
                        subword_sessions,
                        "words_found_count",
                        "מילים שנמצאו בכל משחק (גבוה יותר = טוב יותר)",
                        higher_is_better=True,
                    ),
                    ft.Container(height=16),
                    _game_trend_card(
                        "scramble",
                        "מילים מבולגנות",
                        scramble_sessions,
                        "words_solved_count",
                        "מילים שסודרו בכל משחק (גבוה יותר = טוב יותר)",
                        higher_is_better=True,
                    ),
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
