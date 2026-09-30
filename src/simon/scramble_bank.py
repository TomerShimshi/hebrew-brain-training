import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"


def load_categories() -> dict[str, dict]:
    """Category name -> {"icon": emoji, "words": [...]}, in display order."""
    return json.loads((_DATA_DIR / "scramble_categories.json").read_text(encoding="utf-8"))
