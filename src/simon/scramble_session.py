import random

from simon.freshness import freshness_order
from simon.letter_puzzle import LetterPuzzle, scramble_letters
from simon.storage import new_session_id
from simon.word_levels import ADVANCED, REGULAR


class ScrambleSession:
    """Drives one scrambled-words session within a single category: each
    word is shown as shuffled letter tiles (a LetterPuzzle), and the player
    taps them in order to spell the word. Every word in the category is
    played once, unseen words first (see freshness_order). `words` maps
    each word to a short definition the player can ask for as a clue.

    UI-independent and seedable so word order and scrambles are
    deterministically testable.
    """

    def __init__(
        self,
        category: str,
        words: dict[str, str],
        rng: random.Random | None = None,
        seen_history: list[list[str]] | None = None,
        level: str = REGULAR,
    ) -> None:
        # stable id for the saved progress record (see storage.upsert_session)
        self.log_id = new_session_id()
        self.category = category
        self.level = level
        self._clues = words
        self._rng = rng or random.Random()
        # words the player hasn't met yet come first, so stopping a game
        # early doesn't mean seeing the same opening words every time
        self._queue = freshness_order(list(words), seen_history or [], self._rng)
        self._puzzles: list[LetterPuzzle] = []
        self._clues_shown = 0
        self._advance()

    def _advance(self) -> None:
        answer = self._queue[len(self._puzzles)]
        self.puzzle = LetterPuzzle(answer, scramble_letters(answer, self._rng))
        self._puzzles.append(self.puzzle)
        # advanced words are new vocabulary: show the meaning upfront (and
        # don't count it as a hint) -- unscrambling a word you don't know
        # without its meaning would be guessing, not learning
        self.clue_shown = self.level == ADVANCED

    @property
    def answer(self) -> str:
        return self.puzzle.answer

    @property
    def words_shown(self) -> list[str]:
        return [p.answer for p in self._puzzles]

    @property
    def solved_count(self) -> int:
        return sum(p.solved for p in self._puzzles)

    @property
    def revealed_count(self) -> int:
        return sum(p.revealed for p in self._puzzles)

    @property
    def hints_used(self) -> int:
        return sum(p.hints_used for p in self._puzzles) + self._clues_shown

    @property
    def total_words(self) -> int:
        return len(self._queue)

    @property
    def position(self) -> int:
        """1-based index of the current word within the category."""
        return len(self._puzzles)

    @property
    def has_next_word(self) -> bool:
        return len(self._puzzles) < len(self._queue)

    @property
    def clue(self) -> str:
        return self._clues[self.answer]

    def get_clue(self) -> str:
        """The current word's definition. Counts as a hint the first time
        it's asked for on each word, so re-reading it doesn't add up."""
        if not self.clue_shown and not self.puzzle.done:
            self.clue_shown = True
            self._clues_shown += 1
        return self._clues[self.answer]

    def next_word(self) -> None:
        if self.has_next_word:
            self._advance()
