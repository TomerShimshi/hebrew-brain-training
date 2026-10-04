import json

import pytest

from simon.hebrew_letters import FINAL_TO_BASE
from simon.scramble_bank import _DATA_DIR, load_categories
from simon.word_levels import ADVANCED, LEVELS, REGULAR, topic_words

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשת") | set(FINAL_TO_BASE)


def _all_words(level):
    for name, info in load_categories().items():
        for word, clue in topic_words(info, level).items():
            yield name, word, clue


def test_categories_load_with_icon_and_enough_words():
    categories = load_categories()
    assert len(categories) >= 5
    for name, info in categories.items():
        assert info["icon"], name
        assert len(info["words"]) >= 8, name


def test_advanced_level_has_enough_topics_and_words():
    topics = [name for name, info in load_categories().items() if topic_words(info, ADVANCED)]
    assert len(topics) >= 10
    assert sum(1 for _ in _all_words(ADVANCED)) >= 150


@pytest.mark.parametrize("level", LEVELS)
def test_words_are_plain_hebrew_of_playable_length(level):
    for name, word, _ in _all_words(level):
        assert set(word) <= HEBREW_LETTERS, (name, word)
        assert 3 <= len(word) <= 6, (name, word)
        assert not set(word[:-1]) & set(FINAL_TO_BASE), (name, word)


@pytest.mark.parametrize("level", LEVELS)
def test_every_word_can_actually_be_scrambled(level):
    for name, word, _ in _all_words(level):
        assert len(set(word)) >= 2, (name, word)


@pytest.mark.parametrize("level", LEVELS)
def test_every_word_has_a_clue_that_does_not_give_it_away(level):
    for name, word, clue in _all_words(level):
        assert clue.strip(), (name, word)
        assert word not in clue, (name, word)


def test_no_duplicate_words_within_a_topic_across_levels():
    for name, info in load_categories().items():
        regular, advanced = set(topic_words(info, REGULAR)), set(topic_words(info, ADVANCED))
        assert not regular & advanced, (name, regular & advanced)


def test_no_duplicate_keys_in_the_raw_file():
    # a repeated key would silently collapse into one word when loaded
    def reject_duplicates(pairs):
        keys = [k for k, _ in pairs]
        assert len(keys) == len(set(keys)), {k for k in keys if keys.count(k) > 1}
        return dict(pairs)

    json.loads((_DATA_DIR / "scramble_categories.json").read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
