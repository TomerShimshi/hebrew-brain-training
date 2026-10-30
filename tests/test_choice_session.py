import random

from simon.choice_bank import ChoiceItem, definition_items, load_relation_items
from simon.choice_session import ChoiceSession
from simon.level_suggestions import Outcome, Suggestion
from simon.word_levels import ADVANCED, REGULAR


def _items(n: int, group: str = "") -> list[ChoiceItem]:
    return [ChoiceItem(f"מילה{i}", f"תשובה{i}", group, frozenset({f"תשובה{i}"})) for i in range(n)]


def _session(items, **kwargs) -> ChoiceSession:
    return ChoiceSession(items, rng=random.Random(4), **kwargs)


def _wrong(session: ChoiceSession) -> str:
    return next(o for o in session.options if o != session.item.answer and o not in session.picked)


def test_each_question_has_four_distinct_options_including_the_answer():
    session = _session(_items(12))
    while True:
        assert len(session.options) == 4
        assert len(set(session.options)) == 4
        assert session.item.answer in session.options
        session.pick(session.item.answer)
        if not session.has_next:
            break
        session.next_question()


def test_distractors_never_include_related_words():
    items = _items(8) + [ChoiceItem("חם", "קר", "", frozenset({"קר", "צונן", "תשובה1", "תשובה2"}))]
    for seed in range(20):
        session = ChoiceSession(items, rng=random.Random(seed), question_count=len(items))
        while session.item.prompt != "חם":
            session.next_question()
        assert set(session.options) & session.item.related == {"קר"}
        assert "חם" not in session.options


def test_definition_distractors_come_from_the_same_topic_when_possible():
    categories = {
        "פירות": {"icon": "", "words": {"תפוח": "פרי עגול", "בננה": "פרי צהוב", "ענב": "פרי קטן", "אגס": "פרי ירוק"}},
        "כלים": {"icon": "", "words": {"פטיש": "כלי", "מסור": "כלי", "מברג": "כלי"}},
    }
    items = definition_items(categories, REGULAR)
    assert ChoiceItem("פרי עגול", "תפוח", "פירות", frozenset()) in items
    for seed in range(20):
        session = ChoiceSession(items, rng=random.Random(seed), question_count=len(items))
        for _ in range(len(items)):
            if session.item.group == "פירות":
                assert set(session.options) == {"תפוח", "בננה", "ענב", "אגס"}
            if session.has_next:
                session.next_question()


def test_small_pool_falls_back_to_other_items_and_still_gives_four():
    items = _items(2, "קטן") + _items(6, "גדול")[2:]
    session = _session(items, question_count=len(items))
    for _ in range(len(items)):
        assert len(set(session.options)) == 4
        if session.has_next:
            session.next_question()


def test_wrong_pick_keeps_the_question_open_and_correct_pick_finishes_it():
    session = _session(_items(10))
    wrong = _wrong(session)
    assert session.pick(wrong) is False
    assert wrong in session.picked
    assert not session.done
    assert session.pick(session.item.answer) is True
    assert session.done


def test_picks_after_done_are_ignored():
    session = _session(_items(10))
    session.pick(session.item.answer)
    other = _wrong(session)
    assert session.pick(other) is False
    assert other not in session.picked
    assert session.outcomes == [Outcome.CLEAN]


def test_outcomes_first_second_third_try():
    session = _session(_items(10))
    session.pick(session.item.answer)
    session.next_question()
    session.pick(_wrong(session))
    session.pick(session.item.answer)
    session.next_question()
    session.pick(_wrong(session))
    session.pick(_wrong(session))
    session.pick(session.item.answer)
    assert session.outcomes == [Outcome.CLEAN, Outcome.OK, Outcome.STRUGGLE]
    assert session.first_try_correct == 1
    assert session.answered == 3


def test_plays_question_count_items_unseen_first():
    items = _items(15)
    seen = [[f"תשובה{i}" for i in range(10)]]
    session = _session(items, seen_history=seen)
    assert session.total == 10
    shown = []
    while True:
        shown.append(session.item.answer)
        if not session.has_next:
            break
        session.next_question()
    assert session.answers_shown == shown
    assert set(shown[:5]) == {f"תשובה{i}" for i in range(10, 15)}
    assert len(set(shown)) == 10


def test_level_suggestion_up_after_eight_first_try_answers():
    session = _session(_items(12), question_count=12)
    for i in range(8):
        assert session.level_suggestion() is None
        session.pick(session.item.answer)
        session.next_question()
    assert session.clean_streak == 8
    assert session.level_suggestion() is Suggestion.UP
    session.suggestion_dismissed = True
    assert session.level_suggestion() is None


def test_relation_items_load_both_levels():
    for kind in ("synonyms", "opposites"):
        for level in (REGULAR, ADVANCED):
            items = load_relation_items(kind, level)
            assert len(items) >= 30
            assert all(item.answer in item.related and item.group == "" for item in items)
