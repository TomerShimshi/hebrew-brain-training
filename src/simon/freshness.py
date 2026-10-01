import random


def freshness_order(items: list[str], seen_history: list[list[str]], rng: random.Random) -> list[str]:
    """Orders items so the player meets new material first: items never
    seen before come first, then the rest from the one seen longest ago to
    the one seen most recently. Within each group the order is random, so
    play doesn't become predictable.

    `seen_history` is the player's past games, oldest first, each a list of
    the items shown in that game (as saved by the game's progress store).
    """
    last_seen: dict[str, int] = {}
    for game_index, shown in enumerate(seen_history):
        for item in shown:
            last_seen[item] = game_index
    shuffled = list(items)
    rng.shuffle(shuffled)
    # sorted() is stable, so items with the same key keep their shuffled order
    return sorted(shuffled, key=lambda item: last_seen.get(item, -1))
