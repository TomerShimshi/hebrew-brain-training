from simon.kv_store import InMemoryKeyValueStore
from simon.memory_storage import MemoryProgressStore
from simon.storage import new_session_id


def test_no_last_session_when_empty():
    store = MemoryProgressStore(store=InMemoryKeyValueStore())
    assert store.last_session() is None


def test_record_and_read_last_session():
    store = MemoryProgressStore(store=InMemoryKeyValueStore())
    store.save_session(new_session_id(), pair_count=3, moves=5, mismatches=2, completed=True)
    last = store.last_session()
    assert last["pair_count"] == 3
    assert last["moves"] == 5
    assert last["mismatches"] == 2


def test_persists_across_instances():
    backend = InMemoryKeyValueStore()
    store1 = MemoryProgressStore(store=backend)
    store1.save_session(new_session_id(), pair_count=3, moves=4, mismatches=1, completed=True)

    store2 = MemoryProgressStore(store=backend)
    assert store2.last_session()["moves"] == 4


def test_best_moves_for_returns_none_when_no_sessions_at_that_size():
    store = MemoryProgressStore(store=InMemoryKeyValueStore())
    assert store.best_moves_for(3) is None


def test_best_moves_for_tracks_fewest_per_grid_size():
    store = MemoryProgressStore(store=InMemoryKeyValueStore())
    store.save_session(new_session_id(), pair_count=3, moves=8, mismatches=5, completed=True)
    store.save_session(new_session_id(), pair_count=3, moves=4, mismatches=1, completed=True)
    store.save_session(new_session_id(), pair_count=5, moves=3, mismatches=0, completed=True)

    assert store.best_moves_for(3) == 4
    assert store.best_moves_for(5) == 3


def test_recent_sessions_limited_to_window():
    store = MemoryProgressStore(store=InMemoryKeyValueStore())
    for i in range(5):
        store.save_session(new_session_id(), pair_count=3, moves=i, mismatches=0, completed=True)
    recent = store.recent_sessions(n=3)
    assert len(recent) == 3
    assert [s["moves"] for s in recent] == [2, 3, 4]


def test_unfinished_grid_is_saved_but_not_counted():
    backend = InMemoryKeyValueStore()
    store = MemoryProgressStore(store=backend)
    store.save_session("done", pair_count=3, moves=6, mismatches=3, completed=True)
    store.save_session("partial", pair_count=3, moves=2, mismatches=0, completed=False)
    assert store.best_moves_for(3) == 6
    assert store.last_session()["id"] == "done"
    assert [s["id"] for s in store.recent_sessions()] == ["done"]


def test_grid_saved_mid_game_counts_once_finished():
    store = MemoryProgressStore(store=InMemoryKeyValueStore())
    store.save_session("abc", pair_count=3, moves=1, mismatches=0, completed=False)
    store.save_session("abc", pair_count=3, moves=4, mismatches=1, completed=True)
    assert store.recent_sessions() == [store.last_session()]
    assert store.last_session()["moves"] == 4


def test_records_from_before_the_completed_flag_still_count():
    backend = InMemoryKeyValueStore()
    backend.save("memory_progress_v1", {"sessions": [{"id": "old", "date": "x", "pair_count": 3, "moves": 5, "mismatches": 2}]})
    assert MemoryProgressStore(store=backend).best_moves_for(3) == 5
