import random

import pytest

from simon.kv_store import InMemoryKeyValueStore
from simon.scramble_session import ScrambleSession
from simon.settings_storage import SettingsStore
from simon.word_levels import ADVANCED, REGULAR, topic_words

WORDS = {"שלום": "ברכה כשנפגשים", "חתול": "אומר מיאו"}


def test_word_level_defaults_to_regular():
    assert SettingsStore(store=InMemoryKeyValueStore()).word_level == REGULAR


def test_word_level_is_remembered():
    backend = InMemoryKeyValueStore()
    SettingsStore(store=backend).word_level = ADVANCED
    assert SettingsStore(store=backend).word_level == ADVANCED


def test_unknown_word_level_is_rejected():
    with pytest.raises(ValueError):
        SettingsStore(store=InMemoryKeyValueStore()).word_level = "expert"


def test_topic_words_by_level():
    topic = {"words": {"לחם": "..."}, "advanced": {"קינמון": "..."}}
    assert list(topic_words(topic, REGULAR)) == ["לחם"]
    assert list(topic_words(topic, ADVANCED)) == ["קינמון"]
    assert topic_words({"words": {"לחם": "..."}}, ADVANCED) == {}


def test_advanced_scramble_shows_the_meaning_upfront_without_counting_a_hint():
    session = ScrambleSession("test", WORDS, rng=random.Random(0), level=ADVANCED)
    assert session.clue_shown
    session.get_clue()
    session.next_word()
    assert session.clue_shown
    assert session.hints_used == 0


def test_regular_scramble_keeps_the_meaning_as_a_hint():
    session = ScrambleSession("test", WORDS, rng=random.Random(0))
    assert not session.clue_shown
    session.get_clue()
    assert session.hints_used == 1
