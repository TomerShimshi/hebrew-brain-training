import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"


def load_pairs() -> list[list[dict]]:
    """Each pair is two {"word", "clue"} entries whose words are spelled
    with exactly the same letters (e.g. רופא / אפור)."""
    return json.loads((_DATA_DIR / "change_word_pairs.json").read_text(encoding="utf-8"))
