import random

from simon.change_word_session import ChangeWordSession
from simon.letter_puzzle import GuessResult

PAIRS = [
    [
        {"word": "רופא", "clue": "מטפל בחולים", "hint": "לובש חלוק לבן"},
        {"word": "אפור", "clue": "צבע בין שחור ללבן", "hint": "צבע של פיל"},
    ],
    [
        {"word": "לחם", "clue": "אופים אותו", "hint": "במאפייה"},
        {"word": "מלח", "clue": "מפזרים על האוכל", "hint": "במי הים"},
    ],
    [
        {"word": "חמש", "clue": "אחרי ארבע", "hint": "אצבעות ביד"},
        {"word": "שמח", "clue": "ההפך מעצוב", "hint": "מחייך"},
    ],
]


def _session(seed=0, pair_count=3):
    return ChangeWordSession(PAIRS, rng=random.Random(seed), pair_count=pair_count)


def _type(session, word):
    for letter in word:
        session.puzzle.type_letter(letter)
    return session.puzzle.check_attempt()


def test_stage_one_asks_for_the_first_word_by_its_clue():
    session = _session()
    assert session.stage == 1
    assert session.current is session.first
    assert session.puzzle.answer == session.first["word"]
    assert session.puzzle.typed == []  # no letters handed to the player


def test_cannot_move_on_before_finding_the_first_word():
    session = _session()
    session.next_stage()
    assert session.stage == 1


def test_stage_two_asks_for_the_second_word_from_scratch():
    session = _session()
    assert _type(session, session.first["word"]) == GuessResult.CORRECT
    session.next_stage()
    assert session.stage == 2
    assert session.current is session.second
    assert session.puzzle.answer == session.second["word"]
    assert session.puzzle.typed == []


def test_typing_the_first_word_again_in_stage_two_is_wrong():
    session = _session()
    _type(session, session.first["word"])
    session.next_stage()
    assert _type(session, session.first["word"]) == GuessResult.WRONG


def test_full_round_counts_and_moves_to_next_pair():
    session = _session()
    _type(session, session.first["word"])
    session.next_stage()
    _type(session, session.second["word"])
    assert session.round_done
    assert session.first_words_solved == 1
    assert session.changes_solved == 1
    session.next_pair()
    assert session.position == 2
    assert session.stage == 1


def test_extra_clue_counts_as_one_hint_per_word():
    session = _session()
    assert session.show_extra_clue() == session.first["hint"]
    session.show_extra_clue()
    assert session.hints_used == 1
    session.puzzle.reveal()
    session.next_stage()
    assert not session.extra_clue_shown
    assert session.show_extra_clue() == session.second["hint"]
    assert session.hints_used == 2


def test_revealed_words_do_not_count_as_solved():
    session = _session()
    session.puzzle.reveal()
    session.next_stage()
    session.puzzle.reveal()
    assert session.changes_solved == 0
    assert session.revealed_count == 2


def test_plays_requested_number_of_pairs_each_once():
    session = _session(pair_count=2)
    while session.has_next_pair:
        session.next_pair()
    assert session.total_pairs == 2
    words = {w for shown in session.pairs_shown for w in shown.split(">")}
    assert len(words) == 4


def test_pairs_are_played_in_both_directions():
    firsts = {_session(seed=s, pair_count=1).first["word"] for s in range(40)}
    assert {"רופא", "אפור"} <= firsts


def test_unseen_riddles_are_chosen_first():
    # both directions of a pair count as seen
    history = [["רופא>אפור"], ["מלח>לחם"]]
    for seed in range(10):
        session = ChangeWordSession(PAIRS, rng=random.Random(seed), pair_count=1, seen_history=history)
        assert {session.first["word"], session.second["word"]} == {"חמש", "שמח"}


def test_when_all_seen_the_oldest_riddle_comes_first():
    history = [["לחם>מלח"], ["רופא>אפור"], ["חמש>שמח"]]
    session = ChangeWordSession(PAIRS, rng=random.Random(0), pair_count=1, seen_history=history)
    assert {session.first["word"], session.second["word"]} == {"לחם", "מלח"}
