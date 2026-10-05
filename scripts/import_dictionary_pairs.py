"""Adds hand-picked change-a-word pairs from the ויקימילון candidates
(see find_word_candidates.py) to the riddle banks -- deterministically
checked against the dictionary:

- every word must exist in ויקימילון;
- each pair goes to the level its frequency rank gives it (regular or
  advanced) -- the import refuses a pair placed at the wrong level;
- each entry stores the dictionary's own first definition under
  "definition", next to the short clue written from it, so every clue can
  be traced back to its source.

Usage:
    python scripts/import_dictionary_pairs.py path/to/pairs.json
where pairs.json is {"regular": [[[w, clue, hint], [w, clue, hint]], ...],
"advanced": [...]}.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from find_word_candidates import level_for, load_frequency_ranks  # noqa: E402
from hebrew_wiktionary import load_lookup  # noqa: E402
from simon.hebrew_letters import to_base_form  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "simon" / "data"
FILES = {"regular": "change_word_pairs.json", "advanced": "change_word_pairs_advanced.json"}


def _write(path: Path, pairs: list) -> None:
    lines = []
    for i, (a, b) in enumerate(pairs):
        sep = "," if i < len(pairs) - 1 else ""
        lines.append("  [" + json.dumps(a, ensure_ascii=False) + ",")
        lines.append("   " + json.dumps(b, ensure_ascii=False) + "]" + sep)
    path.write_text("[\n" + "\n".join(lines) + "\n]\n", encoding="utf-8", newline="")


def main(source: Path) -> None:
    lookup, ranks = load_lookup(), load_frequency_ranks()
    new = json.loads(source.read_text(encoding="utf-8"))
    errors = []
    for level, pairs in new.items():
        for first, second in pairs:
            words = [first[0], second[0]]
            if sorted(to_base_form(words[0])) != sorted(to_base_form(words[1])):
                errors.append(f"{words}: not the same letters")
            for w in words:
                if w not in lookup:
                    errors.append(f"{w}: not in ויקימילון")
            rarest = max(ranks.get(w, 10**9) for w in words)
            if level_for(rarest) != level:
                errors.append(f"{words}: belongs to {level_for(rarest)}, not {level}")
    if errors:
        sys.exit("refusing to import:\n  " + "\n  ".join(errors))

    for level, pairs in new.items():
        path = DATA_DIR / FILES[level]
        bank = json.loads(path.read_text(encoding="utf-8"))
        for first, second in pairs:
            bank.append([
                {"word": w, "clue": clue, "hint": hint, "definition": lookup[w]["definitions"][0]}
                for w, clue, hint in (first, second)
            ])
        _write(path, bank)
        print(f"{level}: +{len(pairs)} pairs -> {len(bank)} in {path.name}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
