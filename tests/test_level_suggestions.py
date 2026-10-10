import random
from datetime import date, timedelta
from types import SimpleNamespace

from simon.change_word_session import ChangeWordSession
from simon.kv_store import InMemoryKeyValueStore
from simon.level_suggestions import CHANGE_WORD, SCRAMBLE, Outcome, Suggestion, classify, clean_streak, suggest, worst
from simon.scramble_session import ScrambleSession
from simon.settings_storage import SettingsStore
from simon.word_levels import ADVANCED, REGULAR

CLEAN, OK, STRUGGLE = Outcome.CLEAN, Outcome.OK, Outcome.STRUGGLE


def _puzzle(revealed=False, hints=0):
    return SimpleNamespace(revealed=revealed, hints_used=hints)


# --- rating a word -------------------------------------------------------

def test_classify_outcomes():
    assert classify(_puzzle()) is CLEAN
    assert classify(_puzzle(hints=1)) is OK
    assert classify(_puzzle(hints=2)) is STRUGGLE
    assert classify(_puzzle(revealed=True)) is STRUGGLE


def test_worst_of_two_stages():
    assert worst(CLEAN, CLEAN) is CLEAN
    assert worst(CLEAN, OK) is OK
    assert worst(OK, STRUGGLE) is STRUGGLE


def test_clean_streak_counts_only_the_latest_run():
    assert clean_streak([CLEAN, OK, CLEAN, CLEAN]) == 2
    assert clean_streak([]) == 0


# --- when to suggest -----------------------------------------------------

def test_suggest_up_only_after_a_long_enough_clean_run_at_regular():
    assert suggest(REGULAR, [CLEAN] * 7, SCRAMBLE) is None
    assert suggest(REGULAR, [CLEAN] * 8, SCRAMBLE) is Suggestion.UP
    assert suggest(REGULAR, [CLEAN] * 8 + [OK], SCRAMBLE) is None
    assert suggest(ADVANCED, [CLEAN] * 20, SCRAMBLE) is None  # nowhere higher to go


def test_suggest_down_when_recent_words_were_a_struggle_at_advanced():
    assert suggest(ADVANCED, [STRUGGLE, CLEAN, STRUGGLE], SCRAMBLE) is None
    assert suggest(ADVANCED, [STRUGGLE, CLEAN, STRUGGLE, STRUGGLE], SCRAMBLE) is Suggestion.DOWN
    assert suggest(ADVANCED, [STRUGGLE] * 3 + [CLEAN] * 4, SCRAMBLE) is None  # old struggles age out
    assert suggest(REGULAR, [STRUGGLE] * 10, SCRAMBLE) is None  # nowhere lower to go


def test_suggestion_targets():
    assert Suggestion.UP.target_level == ADVANCED
    assert Suggestion.DOWN.target_level == REGULAR


# --- in a scrambled-words game -------------------------------------------

def _scramble(level=REGULAR, n=12):
    words = {w: "רמז" for w in ["שלום", "חתול", "כלב", "ספר", "גשם", "ירח", "דלת", "חלון", "שמש", "ענן", "פרח", "סוס"][:n]}
    return ScrambleSession("test", words, rng=random.Random(0), level=level)


def _solve(session, clean=True):
    if clean:
        while session.puzzle.hint_next_letter():
            pass
        session.puzzle.hints_used = 0  # placed the letters directly, no help
        session.puzzle.check_attempt()
    else:
        session.puzzle.reveal()
    if session.has_next_word:
        session.next_word()


def test_scramble_suggests_advanced_after_eight_clean_words():
    session = _scramble()
    for _ in range(7):
        _solve(session)
    assert session.level_suggestion() is None
    _solve(session)
    assert session.level_suggestion() is Suggestion.UP
    assert session.clean_streak == 8


def test_a_revealed_word_resets_the_streak():
    session = _scramble()
    for _ in range(7):
        _solve(session)
    _solve(session, clean=False)
    _solve(session)
    assert session.clean_streak == 1
    assert session.level_suggestion() is None


def test_not_now_means_no_more_offers_this_game():
    session = _scramble()
    for _ in range(8):
        _solve(session)
    session.suggestion_dismissed = True
    _solve(session)
    assert session.level_suggestion() is None


def test_scramble_suggests_regular_when_advanced_is_too_hard():
    session = _scramble(level=ADVANCED)
    for _ in range(3):
        _solve(session, clean=False)
    assert session.level_suggestion() is Suggestion.DOWN


# --- in a change-a-word game ---------------------------------------------

PAIRS = [
    [{"word": a, "clue": "c", "hint": "h"}, {"word": b, "clue": "c", "hint": "h"}]
    for a, b in [("רופא", "אפור"), ("לחם", "מלח"), ("חמש", "שמח"), ("ספר", "פרס"), ("גשם", "מגש"), ("ברק", "קרב")]
]


def _round(session, clean=True):
    for _stage in (1, 2):
        if clean:
            while session.puzzle.hint_next_letter():
                pass
            session.puzzle.hints_used = 0
            session.puzzle.check_attempt()
        else:
            session.puzzle.reveal()
        if _stage == 1:
            session.next_stage()
    if session.has_next_pair:
        session.next_pair()


def test_change_word_suggests_advanced_after_five_clean_riddles():
    session = ChangeWordSession(PAIRS, rng=random.Random(0), pair_count=6)
    for _ in range(4):
        _round(session)
    assert session.level_suggestion() is None
    _round(session)
    assert session.level_suggestion() is Suggestion.UP


def test_change_word_suggests_regular_after_two_hard_riddles_at_advanced():
    session = ChangeWordSession(PAIRS, rng=random.Random(0), pair_count=6, level=ADVANCED)
    _round(session, clean=False)
    assert session.level_suggestion() is None
    _round(session, clean=False)
    assert session.level_suggestion() is Suggestion.DOWN


def test_change_word_thresholds_are_smaller_since_a_game_is_eight_riddles():
    assert CHANGE_WORD.up_streak < SCRAMBLE.up_streak


# --- never nag -----------------------------------------------------------

def test_one_decline_does_not_pause_suggestions():
    settings = SettingsStore(store=InMemoryKeyValueStore())
    today = date(2026, 10, 10)
    settings.record_suggestion_declined(today)
    assert not settings.suggestions_paused(today)


def test_two_declines_within_a_week_pause_suggestions_for_a_week():
    backend = InMemoryKeyValueStore()
    settings = SettingsStore(store=backend)
    day1 = date(2026, 10, 10)
    settings.record_suggestion_declined(day1)
    settings.record_suggestion_declined(day1 + timedelta(days=2))
    reloaded = SettingsStore(store=backend)  # remembered across visits
    assert reloaded.suggestions_paused(day1 + timedelta(days=3))
    assert reloaded.suggestions_paused(day1 + timedelta(days=8))
    assert not reloaded.suggestions_paused(day1 + timedelta(days=9))


def test_declines_far_apart_do_not_pause():
    settings = SettingsStore(store=InMemoryKeyValueStore())
    day1 = date(2026, 10, 1)
    settings.record_suggestion_declined(day1)
    settings.record_suggestion_declined(day1 + timedelta(days=20))
    assert not settings.suggestions_paused(day1 + timedelta(days=21))
