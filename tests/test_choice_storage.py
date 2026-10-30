from simon.choice_storage import ChoiceProgressStore
from simon.kv_store import InMemoryKeyValueStore
from simon.storage import new_session_id
from simon.word_levels import ADVANCED


def _record(store, shown, first_try, session_id=None, level=ADVANCED):
    store.save_session(session_id or new_session_id(), shown, first_try, len(shown), level)


def test_saving_same_session_updates_in_place():
    store = ChoiceProgressStore("synonym", store=InMemoryKeyValueStore())
    session_id = new_session_id()
    _record(store, ["קר"], 1, session_id)
    _record(store, ["קר", "קטן"], 1, session_id)
    assert len(store.recent_sessions()) == 1
    last = store.last_session()
    assert last["answers_shown"] == ["קר", "קטן"]
    assert last["answered"] == 2
    assert last["level"] == ADVANCED


def test_games_do_not_share_progress():
    backend = InMemoryKeyValueStore()
    _record(ChoiceProgressStore("synonym", store=backend), ["קר"], 1)
    assert ChoiceProgressStore("opposite", store=backend).last_session() is None
    assert ChoiceProgressStore("synonym", store=backend).last_session()["first_try_correct"] == 1


def test_seen_history_oldest_first():
    store = ChoiceProgressStore("definition", store=InMemoryKeyValueStore())
    _record(store, ["תפוח"], 1)
    _record(store, ["בננה", "ענב"], 2)
    assert store.seen_history() == [["תפוח"], ["בננה", "ענב"]]


def test_best_first_try_correct():
    store = ChoiceProgressStore("opposite", store=InMemoryKeyValueStore())
    assert store.best_first_try_correct() is None
    _record(store, ["א", "ב", "ג"], 2)
    _record(store, ["ד"], 1)
    assert store.best_first_try_correct() == 2
