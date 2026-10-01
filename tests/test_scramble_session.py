import random

from simon.hebrew_letters import to_base_form
from simon.scramble_session import ScrambleSession

WORDS = {
    "שלום": "ברכה כשנפגשים",
    "מלפפון": "ירק ירוק ומאורך",
    "חתול": "אומר מיאו",
}


def _session(words=None, seed=0):
    return ScrambleSession("test", words or WORDS, rng=random.Random(seed))


def test_plays_every_word_once():
    session = _session()
    while session.has_next_word:
        session.next_word()
    assert sorted(session.words_shown) == sorted(WORDS)
    assert session.position == session.total_words == 3


def test_tiles_are_a_scramble_of_the_answer():
    session = _session()
    assert sorted(session.puzzle.tiles) == sorted(to_base_form(session.answer))


def test_counts_add_up_across_words():
    session = _session()
    while session.puzzle.hint_next_letter():
        pass
    session.puzzle.check_attempt()
    session.next_word()
    session.puzzle.reveal()
    assert session.solved_count == 1
    assert session.revealed_count == 1
    assert session.hints_used == len(session.words_shown[0])


def test_clue_is_the_current_words_definition():
    session = _session()
    assert session.get_clue() == WORDS[session.answer]
    assert session.clue_shown


def test_clue_counts_as_one_hint_per_word():
    session = _session()
    session.get_clue()
    session.get_clue()
    assert session.hints_used == 1
    session.next_word()
    assert not session.clue_shown
    session.get_clue()
    assert session.hints_used == 2


def test_unseen_words_come_first():
    history = [["שלום", "חתול"]]
    for seed in range(10):
        session = ScrambleSession("test", WORDS, rng=random.Random(seed), seen_history=history)
        assert session.answer == "מלפפון"


def test_seen_words_still_played_oldest_first():
    session = ScrambleSession("test", WORDS, rng=random.Random(0), seen_history=[["חתול"], ["שלום"]])
    while session.has_next_word:
        session.next_word()
    assert session.words_shown == ["מלפפון", "חתול", "שלום"]
