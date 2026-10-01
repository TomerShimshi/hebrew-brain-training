import random

from simon.freshness import freshness_order

ITEMS = ["א", "ב", "ג", "ד", "ה"]


def test_without_history_returns_all_items_shuffled():
    order = freshness_order(ITEMS, [], random.Random(0))
    assert sorted(order) == sorted(ITEMS)


def test_unseen_items_come_first():
    history = [["א", "ב"], ["ג"]]
    for seed in range(20):
        order = freshness_order(ITEMS, history, random.Random(seed))
        assert set(order[:2]) == {"ד", "ה"}


def test_seen_items_ordered_oldest_first():
    history = [["ג"], ["א"], ["ב"]]
    order = freshness_order(["א", "ב", "ג"], history, random.Random(0))
    assert order == ["ג", "א", "ב"]


def test_an_item_seen_again_counts_by_its_latest_game():
    history = [["א", "ב"], ["א"]]
    order = freshness_order(["א", "ב"], history, random.Random(0))
    assert order == ["ב", "א"]


def test_history_items_not_in_the_candidates_are_ignored():
    order = freshness_order(["א", "ב"], [["ז", "ח"]], random.Random(0))
    assert sorted(order) == ["א", "ב"]
