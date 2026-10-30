"""Questions for the multiple-choice word games (synonym, opposite,
definition), as ChoiceItems the shared ChoiceSession plays.

- synonyms / opposites: from data/synonyms.json and data/opposites.json,
  pairs listed by ויקימילון (see scripts/import_dictionary_relations.py);
- definitions: the scrambled-words clues -- the clue is the question, its
  word the answer, and wrong options come from the same topic first.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from simon.word_levels import topic_words

_DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class ChoiceItem:
    prompt: str  # the word (or definition) shown
    answer: str
    group: str  # topic for the definition game, "" otherwise
    # words never to offer as a wrong option: they could also be right
    related: frozenset[str]


def load_relation_items(kind: str, level: str) -> list[ChoiceItem]:
    """`kind` is "synonyms" or "opposites"."""
    entries = json.loads((_DATA_DIR / f"{kind}.json").read_text(encoding="utf-8"))
    return [
        ChoiceItem(e["word"], e["answer"], "", frozenset(e["related"]))
        for e in entries
        if e["level"] == level
    ]


def definition_items(categories: dict, level: str) -> list[ChoiceItem]:
    return [
        ChoiceItem(clue, word, topic, frozenset())
        for topic, info in categories.items()
        for word, clue in topic_words(info, level).items()
    ]
