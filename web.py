"""ASGI entrypoint for hosting the app as a persistent web service (Render).

Run with: uvicorn web:app --host 0.0.0.0 --port $PORT
Separate from main.py (the desktop dev entrypoint via `flet run`/`python
main.py`) because this returns a FastAPI app for a real server to serve,
rather than blocking to run Flet's own dev/desktop loop.

Built with flet_web directly (the same way ft.run(export_asgi_app=True)
does) so the page shell gets the app's name: without it, the browser tab
says "Flet" while the app loads -- which, on a free server that sleeps when
idle, can be the first thing a visitor sees for half a minute.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import flet_web.fastapi as flet_fastapi  # noqa: E402

from main import APP_TITLE, main  # noqa: E402

app = flet_fastapi.FastAPI()
app.mount(
    "/",
    flet_fastapi.app(
        main,
        assets_dir=str(ROOT / "assets"),
        app_name=APP_TITLE,
        # the label under the icon when added to a phone's home screen
        app_short_name="משחקי אימון",
        app_description="משחקי אימון בעברית לתרגול מילים, זיכרון וזמן תגובה לאחר שבץ",
    ),
)
