import random

from simon.subword_session import CheckResult, SubWordSession, choose_base_word

BANK = {
    "שלום": ["של", "לו", "שלו", "לום"],
    "מכתב": ["מכת", "כתב", "תב"],
}
CLUES = {
    "של": "מילת שייכות",
    "לו": "מכוון אל גבר",
    "שלו": "רגוע ושקט",
    "לום": "חלק מהמילה שלום",
    "מכת": "פגיעה",
    "כתב": "כתיבה, או עיתונאי",
    "תב": "חלק מהמילה מכתב",
}


def _session(base_word="שלום", rng=None):
    return SubWordSession(BANK, CLUES, rng=rng or random.Random(0), base_word=base_word)


def test_starts_with_a_word_from_the_bank():
    session = SubWordSession(BANK, CLUES, rng=random.Random(0))
    assert session.base_word in BANK


def test_tiles_match_base_word_letters_in_order():
    session = _session()
    assert session.tiles == list("שלום")


def test_tap_tile_builds_attempt_in_tap_order():
    session = _session()
    session.tap_tile(2)
    session.tap_tile(0)
    assert session.current_attempt == [2, 0]
    assert session.current_attempt_display() == "וש"


def test_tapping_same_tile_twice_is_ignored():
    session = _session()
    session.tap_tile(0)
    session.tap_tile(0)
    assert session.current_attempt == [0]


def test_undo_last_removes_most_recent_tap():
    session = _session()
    session.tap_tile(0)
    session.tap_tile(1)
    session.undo_last()
    assert session.current_attempt == [0]


def test_undo_last_on_empty_attempt_is_a_no_op():
    session = _session()
    session.undo_last()
    assert session.current_attempt == []


def test_clear_attempt_empties_it_without_touching_found_words():
    session = _session()
    session.tap_tile(0)
    session.tap_tile(1)
    session.check_attempt()  # "של" -> FOUND
    session.tap_tile(2)
    session.clear_attempt()
    assert session.current_attempt == []
    assert session.found_words == ["של"]


def test_check_attempt_too_short_below_two_letters():
    session = _session()
    session.tap_tile(0)
    assert session.check_attempt() == CheckResult.TOO_SHORT
    assert session.current_attempt == [0]  # left intact for editing


def test_check_attempt_found_adds_word_and_clears_attempt():
    session = _session()
    session.tap_tile(0)
    session.tap_tile(1)
    assert session.check_attempt() == CheckResult.FOUND
    assert session.found_words == ["של"]
    assert session.current_attempt == []
    assert session.total_found_count == 1


def test_check_attempt_already_found_does_not_duplicate():
    session = _session()
    session.tap_tile(0)
    session.tap_tile(1)
    session.check_attempt()
    session.tap_tile(0)
    session.tap_tile(1)
    assert session.check_attempt() == CheckResult.ALREADY_FOUND
    assert session.found_words == ["של"]
    assert session.current_attempt == [0, 1]  # left intact
    assert session.total_found_count == 1


def test_check_attempt_not_a_word_leaves_attempt_intact():
    session = _session()
    session.tap_tile(3)
    session.tap_tile(0)
    assert session.check_attempt() == CheckResult.NOT_A_WORD
    assert session.current_attempt == [3, 0]


def test_get_clue_returns_the_clue_for_an_unfound_word():
    session = _session()
    clue = session.get_clue()
    assert clue in CLUES.values()


def test_get_clue_repeats_the_same_word_until_resolved():
    session = SubWordSession(BANK, CLUES, rng=random.Random(1), base_word="שלום")
    first = session.get_clue()
    second = session.get_clue()
    assert first == second


def test_get_clue_returns_none_once_everything_is_found():
    session = _session()
    for _ in range(len(BANK["שלום"])):
        session.reveal_word()
    assert session.get_clue() is None


def test_reveal_word_reveals_the_word_the_pending_clue_was_about():
    session = SubWordSession(BANK, CLUES, rng=random.Random(1), base_word="שלום")
    session.get_clue()
    pending = session._pending_clue_word
    revealed = session.reveal_word()
    assert revealed == pending
    assert revealed in session.found_words


def test_reveal_word_without_a_pending_clue_still_reveals_something():
    session = _session()
    revealed = session.reveal_word()
    assert revealed in BANK["שלום"]
    assert revealed in session.found_words
    assert session.hints_used == 1
    assert session.total_found_count == 1


def test_reveal_word_never_repeats_an_already_found_word():
    session = SubWordSession(BANK, CLUES, rng=random.Random(2), base_word="שלום")
    seen = set()
    for _ in range(len(BANK["שלום"])):
        seen.add(session.reveal_word())
    assert seen == set(BANK["שלום"])


def test_reveal_word_returns_none_once_everything_is_found():
    session = _session()
    for _ in range(len(BANK["שלום"])):
        session.reveal_word()
    assert session.reveal_word() is None


def test_finding_the_pending_clue_word_normally_clears_the_pending_clue():
    session = _session()
    session._pending_clue_word = "של"  # force a known pending clue
    session.tap_tile(0)
    session.tap_tile(1)
    assert session.check_attempt() == CheckResult.FOUND  # "של"
    assert session._pending_clue_word is None


def test_new_base_word_resets_found_words_and_pending_clue():
    session = _session()
    session.tap_tile(0)
    session.tap_tile(1)
    session.check_attempt()
    session.get_clue()
    session.new_base_word()
    assert session.base_word == "מכתב"
    assert session.tiles == list("מכתב")
    assert session.current_attempt == []
    assert session.found_words == []
    assert session._pending_clue_word is None
    assert session.total_found_count == 1  # session-wide total persists


def test_new_base_word_never_immediately_repeats():
    session = _session(rng=random.Random(2))
    for _ in range(10):
        previous = session.base_word
        session.new_base_word()
        assert session.base_word != previous


def test_base_words_shown_tracks_every_word_presented():
    session = _session()
    session.new_base_word()
    session.new_base_word()
    assert session.base_words_shown == ["שלום", "מכתב", "שלום"]


def test_choose_base_word_excludes_given_word_when_alternatives_exist():
    rng = random.Random(0)
    for _ in range(20):
        assert choose_base_word(BANK, rng, exclude="שלום") == "מכתב"


def test_choose_base_word_falls_back_when_only_excluded_word_exists():
    single = {"שלום": ["של"]}
    assert choose_base_word(single, random.Random(0), exclude="שלום") == "שלום"


def test_new_game_prefers_a_base_word_not_seen_before():
    for seed in range(10):
        session = SubWordSession(BANK, CLUES, rng=random.Random(seed), seen_history=[["שלום"]])
        assert session.base_word == "מכתב"


def test_new_word_button_avoids_words_shown_earlier_in_the_game():
    bank = {**BANK, "חלון": ["חל"]}
    session = SubWordSession(bank, CLUES, rng=random.Random(0), base_word="שלום", seen_history=[["מכתב"]])
    session.new_base_word()
    assert session.base_word == "חלון"  # never seen; מכתב was seen in a past game
    session.new_base_word()
    assert session.base_word == "מכתב"  # seen longer ago than this game's שלום
