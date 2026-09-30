import random

from simon.hebrew_letters import to_base_form
from simon.scramble_session import GuessResult, ScrambleSession, scramble_letters

WORDS = {
    "שלום": "ברכה כשנפגשים",
    "מלפפון": "ירק ירוק ומאורך",
    "חתול": "אומר מיאו",
}


def _session(words=None, seed=0):
    return ScrambleSession("test", words or WORDS, rng=random.Random(seed))


def _tap_answer(session):
    """Taps tiles in the order that spells the answer."""
    used = []
    for letter in to_base_form(session.answer):
        index = next(i for i, t in enumerate(session.tiles) if t == letter and i not in used)
        used.append(index)
        session.tap_tile(index)


def test_scramble_is_a_permutation_different_from_the_word():
    rng = random.Random(0)
    for word in ["שלום", "סוס", "מלפפון"]:
        for _ in range(20):
            letters = scramble_letters(word, rng)
            assert sorted(letters) == sorted(to_base_form(word))
            assert "".join(letters) != to_base_form(word)


def test_scramble_uses_non_final_letter_forms():
    letters = scramble_letters("שלום", random.Random(0))
    assert "ם" not in letters
    assert "מ" in letters


def test_plays_every_word_once():
    session = _session()
    while session.has_next_word:
        session.next_word()
    assert sorted(session.words_shown) == sorted(WORDS)
    assert session.position == session.total_words == 3


def test_correct_spelling_solves_the_word():
    session = _session()
    _tap_answer(session)
    assert session.check_attempt() == GuessResult.CORRECT
    assert session.word_done
    assert not session.word_revealed
    assert session.solved_count == 1


def test_partial_attempt_is_incomplete():
    session = _session()
    session.tap_tile(0)
    assert session.check_attempt() == GuessResult.INCOMPLETE
    assert not session.word_done


def test_wrong_full_attempt_is_wrong_and_left_intact():
    session = _session()
    # the scramble itself is guaranteed not to be the answer
    for i in range(len(session.tiles)):
        session.tap_tile(i)
    assert session.check_attempt() == GuessResult.WRONG
    assert session.current_attempt == list(range(len(session.tiles)))
    assert session.solved_count == 0


def test_slot_letters_pad_with_empty_and_apply_final_form_when_full():
    session = _session({"שלום": "ברכה"})
    assert session.slot_letters() == ["", "", "", ""]
    _tap_answer(session)
    assert session.slot_letters() == list("שלום")


def test_hint_places_next_correct_letter():
    session = _session()
    assert session.hint_next_letter()
    assert session.slot_letters()[0] == to_base_form(session.answer)[0]
    assert session.hints_used == 1


def test_hint_drops_wrong_letters_after_correct_prefix():
    session = _session({"שלום": "ברכה"})
    target = to_base_form(session.answer)
    wrong = next(i for i, t in enumerate(session.tiles) if t != target[0])
    session.tap_tile(wrong)
    session.hint_next_letter()
    assert [session.tiles[i] for i in session.current_attempt] == [target[0]]


def test_hints_alone_can_complete_the_word():
    session = _session({"מלפפון": "ירק"})
    while session.hint_next_letter():
        pass
    assert session.check_attempt() == GuessResult.CORRECT
    assert session.slot_letters() == list("מלפפון")


def test_reveal_marks_done_without_solving():
    session = _session()
    session.reveal_word()
    assert session.word_done
    assert session.word_revealed
    assert session.revealed_count == 1
    assert session.solved_count == 0
    assert "".join(session.slot_letters()) == session.answer


def test_taps_ignored_once_word_is_done():
    session = _session()
    session.reveal_word()
    before = list(session.current_attempt)
    session.undo_last()
    session.clear_attempt()
    session.tap_tile(0)
    assert session.current_attempt == before


def test_next_word_resets_attempt_and_state():
    session = _session()
    session.reveal_word()
    session.next_word()
    assert session.current_attempt == []
    assert not session.word_done
    assert not session.word_revealed


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
