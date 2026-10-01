import flet as ft

from simon.app_state import AppState
from simon.scramble_session import ScrambleSession
from simon.ui_helpers import GAME_THEMES, TEXT_SECONDARY, chip_button, rtl_text, soft_shadow

THEME = GAME_THEMES["scramble"]


def build_scramble_categories_view(page: ft.Page, state: AppState) -> ft.View:
    def category_card(name: str, info: dict) -> ft.Container:
        async def on_click(_: ft.ControlEvent) -> None:
            state.scramble_session = ScrambleSession(
                name, info["words"], seen_history=state.scramble_progress.seen_history()
            )
            await page.push_route("/scramble/play")

        return ft.Container(
            content=ft.Column(
                [
                    rtl_text(info["icon"], size=40),
                    rtl_text(name, size=20, weight=ft.FontWeight.BOLD),
                    rtl_text(f"{len(info['words'])} מילים", size=13, color=TEXT_SECONDARY),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor="#FFFFFF",
            border=ft.Border.all(2, THEME["light"]),
            border_radius=20,
            padding=14,
            width=150,
            shadow=soft_shadow(),
            on_click=on_click,
            ink=True,
        )

    async def go_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    return ft.View(
        route="/scramble",
        controls=[
            ft.Column(
                [
                    ft.Row(
                        [chip_button("חזרה לתפריט", go_home, THEME["accent"])],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    rtl_text(f"מילים מבולגנות {THEME['icon']}", size=30, weight=ft.FontWeight.BOLD),
                    rtl_text("בחרו נושא", size=18, color=TEXT_SECONDARY),
                    ft.Container(height=12),
                    ft.Row(
                        [category_card(name, info) for name, info in state.scramble_categories.items()],
                        wrap=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=14,
                        run_spacing=14,
                        width=330,
                    ),
                    ft.Container(height=24),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
