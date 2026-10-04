import random

from simon.freshness import freshness_order
from simon.storage import new_session_id
from simon.typed_puzzle import TypedPuzzle
from simon.word_levels import REGULAR

PAIRS_PER_SESSION = 8


def pair_key(word_a: str, word_b: str) -> str:
    """Identifies a pair regardless of the direction it was played in, so
    playing רופא>אפור counts as having seen אפור>רופא too."""
    return "|".join(sorted((word_a, word_b)))


class ChangeWordSession:
    """Drives one change-a-word session. Each round is a pair of words
    spelled with the same letters, and both are typed from memory on a
    full keyboard, so no letters are ever handed to the player:

    1. from the first word's definition, recall and type it
       (e.g. "מטפל בחולים" -> רופא);
    2. from a new definition, rearrange that word's letters in your head
       and type the new word ("צבע בין שחור ללבן" -> אפור).

    That mental rearranging -- holding a word in working memory and
    manipulating its letters -- is the point of the drill. Each word also
    has an extra clue available as a hint. Riddles the player hasn't seen
    come first, and each is played in a random direction. UI-independent
    and seedable for testing.
    """

    def __init__(
        self,
        pairs: list[list[dict]],
        rng: random.Random | None = None,
        pair_count: int = PAIRS_PER_SESSION,
        seen_history: list[list[str]] | None = None,
        level: str = REGULAR,
    ) -> None:
        """`seen_history` is the player's past games' `pairs_shown` lists,
        oldest first; riddles the player hasn't met yet are chosen first."""
        # stable id for the saved progress record (see storage.upsert_session)
        self.log_id = new_session_id()
        self.level = level
        self._rng = rng or random.Random()
        by_key = {pair_key(a["word"], b["word"]): [a, b] for a, b in pairs}
        history = [[pair_key(*shown.split(">")) for shown in game] for game in seen_history or []]
        fresh_first = freshness_order(list(by_key), history, self._rng)
        chosen = [by_key[key] for key in fresh_first[:pair_count]]
        self._rounds = [self._rng.sample(pair, 2) for pair in chosen]
        self._index = -1
        self._first_puzzles: list[TypedPuzzle] = []
        self._second_puzzles: list[TypedPuzzle] = []
        self._extra_clues_shown = 0
        self.next_pair()

    @property
    def first(self) -> dict:
        return self._rounds[self._index][0]

    @property
    def second(self) -> dict:
        return self._rounds[self._index][1]

    @property
    def stage(self) -> int:
        """1 while finding the first word, 2 while changing it."""
        return 2 if len(self._second_puzzles) > self._index else 1

    @property
    def current(self) -> dict:
        return self.first if self.stage == 1 else self.second

    def _start(self, entry: dict, puzzles: list[TypedPuzzle]) -> None:
        self.puzzle = TypedPuzzle(entry["word"])
        puzzles.append(self.puzzle)
        self.extra_clue_shown = False

    def show_extra_clue(self) -> str:
        """The current word's second clue. Counts as a hint the first time
        it's shown for each word."""
        if not self.extra_clue_shown and not self.puzzle.done:
            self.extra_clue_shown = True
            self._extra_clues_shown += 1
        return self.current["hint"]

    def next_stage(self) -> None:
        if self.stage == 1 and self.puzzle.done:
            self._start(self.second, self._second_puzzles)

    def next_pair(self) -> None:
        if self.has_next_pair:
            self._index += 1
            self._start(self.first, self._first_puzzles)

    @property
    def round_done(self) -> bool:
        return self.stage == 2 and self.puzzle.done

    @property
    def has_next_pair(self) -> bool:
        return self._index + 1 < len(self._rounds)

    @property
    def position(self) -> int:
        """1-based index of the current pair."""
        return self._index + 1

    @property
    def total_pairs(self) -> int:
        return len(self._rounds)

    @property
    def pairs_shown(self) -> list[str]:
        return [f"{a['word']}>{b['word']}" for a, b in self._rounds[: self._index + 1]]

    @property
    def changes_solved(self) -> int:
        """Second-stage words solved without revealing -- the game's main
        skill (finding a new word hidden in the same letters)."""
        return sum(p.solved for p in self._second_puzzles)

    @property
    def first_words_solved(self) -> int:
        return sum(p.solved for p in self._first_puzzles)

    @property
    def revealed_count(self) -> int:
        return sum(p.revealed for p in self._first_puzzles + self._second_puzzles)

    @property
    def hints_used(self) -> int:
        letter_hints = sum(p.hints_used for p in self._first_puzzles + self._second_puzzles)
        return letter_hints + self._extra_clues_shown
