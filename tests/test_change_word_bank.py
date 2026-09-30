from simon.change_word_bank import load_pairs
from simon.hebrew_letters import FINAL_TO_BASE, to_base_form

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשת") | set(FINAL_TO_BASE)


def _words():
    for pair in load_pairs():
        yield from pair


def test_bank_has_enough_pairs():
    assert len(load_pairs()) >= 30


def test_each_pair_is_two_different_words_with_the_same_letters():
    for first, second in load_pairs():
        assert first["word"] != second["word"], first["word"]
        assert sorted(to_base_form(first["word"])) == sorted(to_base_form(second["word"])), (first["word"], second["word"])


def test_words_are_plain_hebrew_of_playable_length():
    for entry in _words():
        word = entry["word"]
        assert set(word) <= HEBREW_LETTERS, word
        assert 3 <= len(word) <= 6, word
        assert not set(word[:-1]) & set(FINAL_TO_BASE), word


def test_every_word_has_a_clue_and_extra_clue_that_give_away_neither_word():
    for first, second in load_pairs():
        for entry in (first, second):
            for key in ("clue", "hint"):
                text = entry[key]
                assert text.strip(), (entry["word"], key)
                assert first["word"] not in text, (entry["word"], key, first["word"])
                assert second["word"] not in text, (entry["word"], key, second["word"])


def test_no_word_repeats_across_pairs():
    words = [entry["word"] for entry in _words()]
    assert len(words) == len(set(words))
