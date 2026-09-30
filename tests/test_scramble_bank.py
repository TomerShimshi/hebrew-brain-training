from simon.hebrew_letters import FINAL_TO_BASE
from simon.scramble_bank import load_categories

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשת") | set(FINAL_TO_BASE)


def test_categories_load_with_icon_and_enough_words():
    categories = load_categories()
    assert len(categories) >= 5
    for name, info in categories.items():
        assert info["icon"], name
        assert len(info["words"]) >= 8, name


def test_words_are_plain_hebrew_of_playable_length():
    for name, info in load_categories().items():
        for word in info["words"]:
            assert set(word) <= HEBREW_LETTERS, (name, word)
            assert 3 <= len(word) <= 6, (name, word)


def test_every_word_can_actually_be_scrambled():
    for name, info in load_categories().items():
        for word in info["words"]:
            assert len(set(word)) >= 2, (name, word)


def test_no_duplicate_words_within_a_category():
    for name, info in load_categories().items():
        assert len(info["words"]) == len(set(info["words"])), name


def test_final_letters_only_at_word_end():
    for name, info in load_categories().items():
        for word in info["words"]:
            assert not set(word[:-1]) & set(FINAL_TO_BASE), (name, word)


def test_every_word_has_a_clue_that_does_not_give_it_away():
    for name, info in load_categories().items():
        for word, clue in info["words"].items():
            assert clue.strip(), (name, word)
            assert word not in clue, (name, word)
