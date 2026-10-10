import random

from simon import level_suggestions
from simon.freshness import freshness_order
from simon.hebrew_letters import to_base_form
from simon.letter_puzzle import LetterPuzzle
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
    spelled with the same letters, played in two stages:

    1. from the first word's definition, recall it and type it on a full
       keyboard -- no letters handed over (e.g. "מטפל בחולים" -> רופא);
    2. from a new definition, rearrange that word's letters into the new
       word ("צבע בין שחור ללבן" -> אפור), by tapping them as letter tiles
       (a LetterPuzzle, like the scrambled-words game) -- offering only
       those letters keeps the task about rearranging, which a full
       keyboard here made confusing.

    Each word also
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
        self._second_puzzles: list[LetterPuzzle] = []
        self._extra_clues_shown = 0
        self.suggestion_dismissed = False
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

    def _start(self, puzzle: TypedPuzzle | LetterPuzzle, puzzles: list) -> None:
        self.puzzle = puzzle
        puzzles.append(puzzle)
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
            # the first word's letters as tiles, in that word's order
            tiles = list(to_base_form(self.first["word"]))
            self._start(LetterPuzzle(self.second["word"], tiles), self._second_puzzles)

    def next_pair(self) -> None:
        if self.has_next_pair:
            self._index += 1
            self._start(TypedPuzzle(self.first["word"]), self._first_puzzles)

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
    def outcomes(self) -> list[level_suggestions.Outcome]:
        """How each finished riddle went (both stages; the harder of the two
        counts), in order -- see level_suggestions."""
        return [
            level_suggestions.worst(level_suggestions.classify(first), level_suggestions.classify(second))
            for first, second in zip(self._first_puzzles, self._second_puzzles)
            if second.done
        ]

    @property
    def clean_streak(self) -> int:
        return level_suggestions.clean_streak(self.outcomes)

    def level_suggestion(self) -> level_suggestions.Suggestion | None:
        """Whether to offer a change of level now -- nothing once the player
        said "not now" in this game."""
        if self.suggestion_dismissed:
            return None
        return level_suggestions.suggest(self.level, self.outcomes, level_suggestions.CHANGE_WORD)

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
