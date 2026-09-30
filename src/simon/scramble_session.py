import enum
import random

from simon.hebrew_letters import to_base_form, to_display_form
from simon.storage import new_session_id


class GuessResult(enum.Enum):
    INCOMPLETE = "incomplete"
    WRONG = "wrong"
    CORRECT = "correct"


def scramble_letters(word: str, rng: random.Random) -> list[str]:
    """Shuffles the word's letters (in non-final form, so a sofit letter
    never shows up mid-scramble) into an order different from the word
    itself. A word with only one distinct letter can't be scrambled and is
    returned as-is -- the curated bank has none of those."""
    target = to_base_form(word)
    letters = list(target)
    if len(set(letters)) < 2:
        return letters
    while True:
        rng.shuffle(letters)
        if "".join(letters) != target:
            return letters


class ScrambleSession:
    """Drives one scrambled-words session within a single category: each
    word is shown as shuffled letter tiles, and the player taps them in
    order to spell the word. Every word in the category is played once, in
    random order. `words` maps each word to a short definition the player
    can ask for as a clue.

    UI-independent and seedable so word order and scrambles are
    deterministically testable.
    """

    def __init__(self, category: str, words: dict[str, str], rng: random.Random | None = None) -> None:
        # stable id for the saved progress record, so repeated saves during
        # the session update one record instead of adding new ones
        self.log_id = new_session_id()
        self.category = category
        self._clues = words
        self._rng = rng or random.Random()
        self._queue = list(words)
        self._rng.shuffle(self._queue)
        self._next_index = 0
        self.words_shown: list[str] = []
        self.solved_count = 0
        self.revealed_count = 0
        self.hints_used = 0
        self._advance()

    def _advance(self) -> None:
        self.answer = self._queue[self._next_index]
        self._next_index += 1
        self.tiles: list[str] = scramble_letters(self.answer, self._rng)
        self.current_attempt: list[int] = []
        self.word_done = False
        self.word_revealed = False
        self.clue_shown = False
        self.words_shown.append(self.answer)

    @property
    def total_words(self) -> int:
        return len(self._queue)

    @property
    def position(self) -> int:
        """1-based index of the current word within the category."""
        return self._next_index

    @property
    def has_next_word(self) -> bool:
        return self._next_index < len(self._queue)

    def tap_tile(self, index: int) -> None:
        if not self.word_done and index not in self.current_attempt:
            self.current_attempt.append(index)

    def undo_last(self) -> None:
        if not self.word_done and self.current_attempt:
            self.current_attempt.pop()

    def clear_attempt(self) -> None:
        if not self.word_done:
            self.current_attempt = []

    def is_attempt_full(self) -> bool:
        return len(self.current_attempt) == len(self.tiles)

    def slot_letters(self) -> list[str]:
        """One entry per letter of the answer: the placed letter, or "" for
        a still-empty slot. The final-form substitution is applied only
        once every slot is filled, so a half-built word never shows a sofit
        letter in the middle."""
        placed = "".join(self.tiles[i] for i in self.current_attempt)
        if self.is_attempt_full():
            placed = to_display_form(placed)
        return list(placed) + [""] * (len(self.tiles) - len(placed))

    def check_attempt(self) -> GuessResult:
        if self.word_done:
            return GuessResult.CORRECT
        if not self.is_attempt_full():
            return GuessResult.INCOMPLETE
        attempt = "".join(self.tiles[i] for i in self.current_attempt)
        if attempt != to_base_form(self.answer):
            return GuessResult.WRONG
        self.word_done = True
        self.solved_count += 1
        return GuessResult.CORRECT

    def _correct_prefix_length(self) -> int:
        target = to_base_form(self.answer)
        length = 0
        for i, tile_index in enumerate(self.current_attempt):
            if self.tiles[tile_index] != target[i]:
                break
            length += 1
        return length

    def hint_next_letter(self) -> bool:
        """Places the next correct letter: first drops anything after the
        correctly-spelled prefix, then appends an unused tile carrying the
        next letter of the answer. Counts as a hint. Returns False (and
        does nothing) if the word is already done or fully spelled."""
        if self.word_done:
            return False
        target = to_base_form(self.answer)
        keep = self._correct_prefix_length()
        if keep == len(target):
            return False
        self.current_attempt = self.current_attempt[:keep]
        needed = target[keep]
        for i, letter in enumerate(self.tiles):
            if letter == needed and i not in self.current_attempt:
                self.current_attempt.append(i)
                break
        self.hints_used += 1
        return True

    def get_clue(self) -> str:
        """The current word's definition. Counts as a hint the first time
        it's asked for on each word, so re-reading it doesn't add up."""
        if not self.clue_shown and not self.word_done:
            self.clue_shown = True
            self.hints_used += 1
        return self._clues[self.answer]

    def reveal_word(self) -> None:
        """Gives up on the current word: fills the slots with the correct
        spelling and marks the word done without counting it as solved."""
        if self.word_done:
            return
        unused = list(range(len(self.tiles)))
        attempt = []
        for letter in to_base_form(self.answer):
            match = next(i for i in unused if self.tiles[i] == letter)
            unused.remove(match)
            attempt.append(match)
        self.current_attempt = attempt
        self.word_done = True
        self.word_revealed = True
        self.revealed_count += 1

    def next_word(self) -> None:
        if self.has_next_word:
            self._advance()
