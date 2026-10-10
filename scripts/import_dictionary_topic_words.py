"""Adds hand-picked scrambled-words entries from the ויקימילון topic
candidates (see find_word_candidates.py and topic_categories.json),
deterministically checked against the dictionary:

- every word must exist in ויקימילון and be playable (3-6 letters);
- each word goes to the level its frequency rank gives it -- the import
  refuses a word placed at the wrong level (a dictionary word too rare for
  the frequency list counts as advanced; see level_for);
- the dictionary's first definition of each word is recorded in
  src/simon/data/scramble_sources.json, so every clue can be traced back.

Usage:
    python scripts/import_dictionary_topic_words.py path/to/words.json
where words.json is {topic: {"regular": {word: clue}, "advanced": {word: clue}}}.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from find_word_candidates import is_playable, level_for, load_frequency_ranks  # noqa: E402
from hebrew_wiktionary import load_lookup  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "simon" / "data"
BANK = DATA_DIR / "scramble_categories.json"
SOURCES = DATA_DIR / "scramble_sources.json"
LEVEL_KEY = {"regular": "words", "advanced": "advanced"}


def main(source: Path) -> None:
    lookup, ranks = load_lookup(), load_frequency_ranks()
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    new = json.loads(source.read_text(encoding="utf-8"))
    errors = []
    for topic, levels in new.items():
        if topic not in bank:
            errors.append(f"{topic}: unknown topic")
            continue
        existing = set(bank[topic]["words"]) | set(bank[topic].get("advanced", {}))
        for level, words in levels.items():
            for word in words:
                if word not in lookup:
                    errors.append(f"{topic}/{word}: not in ויקימילון")
                elif not is_playable(word):
                    errors.append(f"{topic}/{word}: not playable")
                elif level_for(ranks.get(word), allow_rare=True) != level:
                    errors.append(f"{topic}/{word}: belongs to {level_for(ranks.get(word), allow_rare=True)}, not {level}")
                if word in existing:
                    errors.append(f"{topic}/{word}: already in the topic")
    if errors:
        sys.exit("refusing to import:\n  " + "\n  ".join(errors))

    sources = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else {}
    added = 0
    for topic, levels in new.items():
        for level, words in levels.items():
            target = bank[topic].setdefault(LEVEL_KEY[level], {})
            for word, clue in words.items():
                target[word] = clue
                sources[word] = lookup[word]["definitions"][0]
                added += 1
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    SOURCES.write_text(json.dumps(dict(sorted(sources.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="")
    print(f"+{added} words; sources recorded for {len(sources)} words")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
