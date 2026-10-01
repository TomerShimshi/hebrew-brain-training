from simon.change_word_storage import ChangeWordProgressStore
from simon.kv_store import InMemoryKeyValueStore


def _save(store, session_id, changes):
    store.save_session(
        session_id,
        pairs_shown=["רופא>אפור"],
        changes_solved=changes,
        first_words_solved=changes,
        hints_used=0,
        revealed_count=0,
    )


def test_empty_store():
    store = ChangeWordProgressStore(store=InMemoryKeyValueStore())
    assert store.last_session() is None
    assert store.best_changes_solved() is None


def test_saving_same_session_again_updates_it_in_place():
    backend = InMemoryKeyValueStore()
    store = ChangeWordProgressStore(store=backend)
    _save(store, "abc", 1)
    _save(store, "abc", 2)
    sessions = ChangeWordProgressStore(store=backend).recent_sessions()
    assert len(sessions) == 1
    assert sessions[0]["changes_solved"] == 2


def test_best_changes_solved():
    store = ChangeWordProgressStore(store=InMemoryKeyValueStore())
    for i, changes in enumerate([2, 5, 3]):
        _save(store, str(i), changes)
    assert store.best_changes_solved() == 5


def test_seen_history_lists_pairs_per_game():
    store = ChangeWordProgressStore(store=InMemoryKeyValueStore())
    _save(store, "a", 1)
    assert store.seen_history() == [["רופא>אפור"]]
