import pytest

from simon.change_word_bank import load_all_pairs, load_pairs
from simon.hebrew_letters import FINAL_TO_BASE, to_base_form
from simon.word_levels import ADVANCED, LEVELS, REGULAR

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשת") | set(FINAL_TO_BASE)


def _words(pairs):
    for pair in pairs:
        yield from pair


@pytest.mark.parametrize("level,minimum", [(REGULAR, 200), (ADVANCED, 30)])
def test_bank_has_enough_pairs(level, minimum):
    assert len(load_pairs(level)) >= minimum


@pytest.mark.parametrize("level", LEVELS)
def test_each_pair_is_two_different_words_with_the_same_letters(level):
    for first, second in load_pairs(level):
        assert first["word"] != second["word"], first["word"]
        assert sorted(to_base_form(first["word"])) == sorted(to_base_form(second["word"])), (first["word"], second["word"])


@pytest.mark.parametrize("level", LEVELS)
def test_words_are_plain_hebrew_of_playable_length(level):
    for entry in _words(load_pairs(level)):
        word = entry["word"]
        assert set(word) <= HEBREW_LETTERS, word
        assert 3 <= len(word) <= 6, word
        assert not set(word[:-1]) & set(FINAL_TO_BASE), word


@pytest.mark.parametrize("level", LEVELS)
def test_every_word_has_a_clue_and_extra_clue_that_give_away_neither_word(level):
    for first, second in load_pairs(level):
        for entry in (first, second):
            for key in ("clue", "hint"):
                text = entry[key]
                assert text.strip(), (entry["word"], key)
                assert first["word"] not in text, (entry["word"], key, first["word"])
                assert second["word"] not in text, (entry["word"], key, second["word"])


def test_no_word_repeats_across_pairs_or_levels():
    words = [entry["word"] for pairs in load_all_pairs().values() for entry in _words(pairs)]
    repeated = {w for w in words if words.count(w) > 1}
    assert not repeated
