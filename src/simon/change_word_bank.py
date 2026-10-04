import json
from pathlib import Path

from simon.word_levels import ADVANCED, LEVELS

_DATA_DIR = Path(__file__).resolve().parent / "data"
_FILES = {level: f"change_word_pairs{'_advanced' if level == ADVANCED else ''}.json" for level in LEVELS}


def load_pairs(level: str) -> list[list[dict]]:
    """Each pair is two {"word", "clue", "hint"} entries whose words are
    spelled with exactly the same letters (e.g. רופא / אפור)."""
    return json.loads((_DATA_DIR / _FILES[level]).read_text(encoding="utf-8"))


def load_all_pairs() -> dict[str, list[list[dict]]]:
    return {level: load_pairs(level) for level in LEVELS}
