"""Adds hand-picked synonym and opposite pairs (from find_word_candidates.py
--relations) to the choice-game banks, deterministically checked against
ויקימילון:

- both words must be dictionary words (single Hebrew words);
- the dictionary must list the pair as synonyms / opposites, in either
  direction -- so the game's "right answer" is always the dictionary's;
- the pair's level is set by its rarer word's frequency rank (a word too
  rare for the frequency list counts as advanced; see level_for);
- each entry stores "related": every word the dictionary relates to either
  word as a synonym or opposite, so the game never offers one of those as a
  wrong option.

Usage:
    python scripts/import_dictionary_relations.py path/to/pairs.json
where pairs.json is {"synonyms": [[word, answer], ...], "opposites": [[word, answer], ...]}.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from find_word_candidates import level_for, load_frequency_ranks  # noqa: E402
from hebrew_wiktionary import _is_playable, load_lookup, related_words  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "simon" / "data"
FILES = {"synonyms": "synonyms.json", "opposites": "opposites.json"}


def _listed(lookup: dict, kind: str, a: str, b: str) -> bool:
    return b in lookup[a].get(kind, []) or a in lookup[b].get(kind, [])


def _write(path: Path, entries: list[dict]) -> None:
    lines = [json.dumps(e, ensure_ascii=False) for e in entries]
    path.write_text("[\n  " + ",\n  ".join(lines) + "\n]\n", encoding="utf-8", newline="")


def main(source: Path) -> None:
    lookup, ranks = load_lookup(), load_frequency_ranks()
    new = json.loads(source.read_text(encoding="utf-8"))
    errors = []
    for kind, pairs in new.items():
        if kind not in FILES:
            errors.append(f"{kind}: unknown bank")
            continue
        path = DATA_DIR / FILES[kind]
        existing = {e["word"] for e in json.loads(path.read_text(encoding="utf-8"))} if path.exists() else set()
        seen = set()
        for word, answer in pairs:
            for w in (word, answer):
                if not _is_playable(w):
                    errors.append(f"{kind}/{w}: not a single Hebrew word")
                elif w not in lookup:
                    errors.append(f"{kind}/{w}: not in ויקימילון")
            if word in lookup and answer in lookup and not _listed(lookup, kind, word, answer):
                errors.append(f"{kind}/{word}~{answer}: not listed by ויקימילון as {kind}")
            if word in existing or word in seen:
                errors.append(f"{kind}/{word}: already in the bank")
            seen.add(word)
    if errors:
        sys.exit("refusing to import:\n  " + "\n  ".join(errors))

    for kind, pairs in new.items():
        path = DATA_DIR / FILES[kind]
        bank = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        for word, answer in pairs:
            related = (related_words(lookup, word) | related_words(lookup, answer) | {word, answer}) - {word}
            bank.append({
                "word": word,
                "answer": answer,
                "level": level_for(max(ranks.get(word, 10**9), ranks.get(answer, 10**9)), allow_rare=True),
                "related": sorted(related),
            })
        _write(path, bank)
        print(f"{kind}: +{len(pairs)} -> {len(bank)} in {path.name}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
