from simon.kv_store import InMemoryKeyValueStore
from simon.scramble_storage import ScrambleProgressStore
from simon.storage import new_session_id


def _record(store, solved, session_id=None):
    store.save_session(
        session_id or new_session_id(),
        category="אוכל",
        words_shown=["לחם"],
        words_solved_count=solved,
        hints_used=0,
        revealed_count=0,
    )


def test_no_last_session_when_empty():
    store = ScrambleProgressStore(store=InMemoryKeyValueStore())
    assert store.last_session() is None
    assert store.best_words_solved_count() is None


def test_record_and_read_last_session():
    store = ScrambleProgressStore(store=InMemoryKeyValueStore())
    _record(store, 3)
    last = store.last_session()
    assert last["category"] == "אוכל"
    assert last["words_solved_count"] == 3


def test_persists_across_instances():
    backend = InMemoryKeyValueStore()
    _record(ScrambleProgressStore(store=backend), 2)
    assert ScrambleProgressStore(store=backend).last_session()["words_solved_count"] == 2


def test_best_and_recent_sessions():
    store = ScrambleProgressStore(store=InMemoryKeyValueStore())
    for solved in [1, 5, 2, 4]:
        _record(store, solved)
    assert store.best_words_solved_count() == 5
    assert [s["words_solved_count"] for s in store.recent_sessions(n=2)] == [2, 4]


def test_saving_same_session_again_updates_it_in_place():
    backend = InMemoryKeyValueStore()
    store = ScrambleProgressStore(store=backend)
    _record(store, 1, session_id="abc")
    first_date = store.last_session()["date"]
    _record(store, 2, session_id="abc")
    _record(store, 3, session_id="abc")
    sessions = ScrambleProgressStore(store=backend).recent_sessions()
    assert len(sessions) == 1
    assert sessions[0]["words_solved_count"] == 3
    assert sessions[0]["date"] == first_date
