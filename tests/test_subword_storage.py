from simon.kv_store import InMemoryKeyValueStore
from simon.storage import new_session_id
from simon.subword_storage import SubWordProgressStore


def test_no_last_session_when_empty():
    store = SubWordProgressStore(store=InMemoryKeyValueStore())
    assert store.last_session() is None


def test_record_and_read_last_session():
    store = SubWordProgressStore(store=InMemoryKeyValueStore())
    store.save_session(new_session_id(), base_words=["שלום"], words_found_count=2, hints_used=1)
    last = store.last_session()
    assert last["base_words"] == ["שלום"]
    assert last["words_found_count"] == 2
    assert last["hints_used"] == 1


def test_persists_across_instances():
    backend = InMemoryKeyValueStore()
    store1 = SubWordProgressStore(store=backend)
    store1.save_session(new_session_id(), base_words=["שלום"], words_found_count=1, hints_used=0)

    store2 = SubWordProgressStore(store=backend)
    assert store2.last_session()["words_found_count"] == 1


def test_best_words_found_count_none_when_empty():
    store = SubWordProgressStore(store=InMemoryKeyValueStore())
    assert store.best_words_found_count() is None


def test_best_words_found_count_tracks_the_max():
    store = SubWordProgressStore(store=InMemoryKeyValueStore())
    store.save_session(new_session_id(), base_words=["שלום"], words_found_count=1, hints_used=0)
    store.save_session(new_session_id(), base_words=["מכתב"], words_found_count=3, hints_used=1)
    assert store.best_words_found_count() == 3


def test_recent_sessions_limited_to_window():
    store = SubWordProgressStore(store=InMemoryKeyValueStore())
    for i in range(5):
        store.save_session(new_session_id(), base_words=["שלום"], words_found_count=i, hints_used=0)
    recent = store.recent_sessions(n=3)
    assert len(recent) == 3
    assert [s["words_found_count"] for s in recent] == [2, 3, 4]


def test_saving_same_session_again_updates_it_in_place():
    backend = InMemoryKeyValueStore()
    store = SubWordProgressStore(store=backend)
    store.save_session("abc", base_words=["שלום"], words_found_count=1, hints_used=0)
    store.save_session("abc", base_words=["שלום", "מכתב"], words_found_count=2, hints_used=0)
    sessions = SubWordProgressStore(store=backend).recent_sessions()
    assert len(sessions) == 1
    assert sessions[0]["words_found_count"] == 2
    assert sessions[0]["base_words"] == ["שלום", "מכתב"]


def test_seen_history_lists_base_words_per_game():
    store = SubWordProgressStore(store=InMemoryKeyValueStore())
    store.save_session("a", base_words=["שלום", "מכתב"], words_found_count=2, hints_used=0)
    assert store.seen_history() == [["שלום", "מכתב"]]
