import random

from simon.storage import new_session_id

DEFAULT_PAIR_COUNT = 10

# Pictures rather than words or colors: matching by picture needs no reading
# or word-finding, which matters since language/word recall is the harder
# deficit for this player -- this game exercises visual/spatial memory
# instead, deliberately independent of verbal ability.
SYMBOLS = [
    "🍎", "🐶", "⭐", "🚗", "🌙", "🎈", "🐱", "🌸",
    "🎵", "⚽", "🍌", "🦋", "🐢", "🍕", "🌈", "🔑",
]
MAX_PAIR_COUNT = len(SYMBOLS)


class MemoryGameSession:
    """Drives one memory-matching (concentration) session: a shuffled grid
    of `pair_count` symbol pairs, flipped two at a time until all are
    matched. Always completable -- no losing state -- since the goal is
    gentle visual/spatial memory practice, not a pass/fail test.

    UI-independent and seedable so shuffling is deterministically testable.
    """

    def __init__(self, pair_count: int = DEFAULT_PAIR_COUNT, rng: random.Random | None = None) -> None:
        pair_count = max(1, min(pair_count, MAX_PAIR_COUNT))
        rng = rng or random.Random()
        cards = SYMBOLS[:pair_count] * 2
        rng.shuffle(cards)

        # stable id for the saved progress record (see storage.upsert_session)
        self.log_id = new_session_id()
        self.cards: list[str] = cards
        self.matched: set[int] = set()
        self.revealed: list[int] = []  # 0, 1, or 2 indices awaiting resolve()
        self.moves = 0
        self.mismatches = 0

    @property
    def pair_count(self) -> int:
        return len(self.cards) // 2

    @property
    def is_complete(self) -> bool:
        return len(self.matched) == len(self.cards)

    def reveal(self, index: int) -> bool:
        """Flips one card face-up. Returns True once a second card has been
        revealed, signaling the caller to show both briefly then call
        resolve(). Taps on an already-matched or already-revealed card are
        ignored (returns False)."""
        if index in self.matched or index in self.revealed:
            return False
        self.revealed.append(index)
        return len(self.revealed) == 2

    def resolve(self) -> bool:
        """Call once two cards are revealed: scores the pair, updates match
        state, and clears `revealed` either way. Returns whether it matched."""
        if len(self.revealed) != 2:
            raise RuntimeError("resolve() requires two revealed cards")
        i, j = self.revealed
        self.moves += 1
        is_match = self.cards[i] == self.cards[j]
        if is_match:
            self.matched.add(i)
            self.matched.add(j)
        else:
            self.mismatches += 1
        self.revealed = []
        return is_match
