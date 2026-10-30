import json
from pathlib import Path

import pytest

from simon.hebrew_letters import FINAL_TO_BASE

DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "simon" / "data"
HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשת") | set(FINAL_TO_BASE)
BANKS = ["synonyms", "opposites"]


def _bank(name: str) -> list[dict]:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", BANKS)
@pytest.mark.parametrize("level,minimum", [("regular", 40), ("advanced", 30)])
def test_bank_has_enough_entries(name, level, minimum):
    assert sum(entry["level"] == level for entry in _bank(name)) >= minimum


@pytest.mark.parametrize("name", BANKS)
def test_entries_are_single_hebrew_words(name):
    for entry in _bank(name):
        for word in (entry["word"], entry["answer"]):
            assert set(word) <= HEBREW_LETTERS, (name, word)
            assert 2 <= len(word) <= 8, (name, word)
            assert not set(word[:-1]) & set(FINAL_TO_BASE), (name, word)


@pytest.mark.parametrize("name", BANKS)
def test_no_word_repeats_within_a_bank(name):
    words = [entry["word"] for entry in _bank(name)]
    assert len(words) == len(set(words))


@pytest.mark.parametrize("name", BANKS)
def test_answer_is_in_related_and_word_is_not(name):
    for entry in _bank(name):
        assert entry["answer"] in entry["related"], entry["word"]
        assert entry["word"] not in entry["related"], entry["word"]
