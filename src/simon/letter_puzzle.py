import enum
import random

from simon.hebrew_letters import to_base_form, to_display_form


class GuessResult(enum.Enum):
    INCOMPLETE = "incomplete"
    WRONG = "wrong"
    CORRECT = "correct"


def scramble_letters(word: str, rng: random.Random) -> list[str]:
    """Shuffles the word's letters (in non-final form, so a sofit letter
    never shows up mid-scramble) into an order different from the word
    itself. A word with only one distinct letter can't be scrambled and is
    returned as-is -- the curated banks have none of those."""
    target = to_base_form(word)
    letters = list(target)
    if len(set(letters)) < 2:
        return letters
    while True:
        rng.shuffle(letters)
        if "".join(letters) != target:
            return letters


class LetterPuzzle:
    """One word to spell by tapping letter tiles into answer slots, in
    order. Shared by the letter-tile games (scrambled words, change-a-word)
    so they behave identically: same tapping, undo, hints and checking.

    `tiles` must be the answer's letters in non-final form, in the order
    they're shown to the player.
    """

    def __init__(self, answer: str, tiles: list[str]) -> None:
        self.answer = answer
        self.tiles = tiles
        self.current_attempt: list[int] = []
        self.solved = False
        self.revealed = False
        self.hints_used = 0

    @property
    def done(self) -> bool:
        return self.solved or self.revealed

    def tap_tile(self, index: int) -> None:
        if not self.done and index not in self.current_attempt:
            self.current_attempt.append(index)

    def undo_last(self) -> None:
        if not self.done and self.current_attempt:
            self.current_attempt.pop()

    def clear_attempt(self) -> None:
        if not self.done:
            self.current_attempt = []

    # the same editing names as TypedPuzzle, so a screen can drive either
    backspace = undo_last
    clear = clear_attempt

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
        if self.done:
            return GuessResult.CORRECT
        if not self.is_attempt_full():
            return GuessResult.INCOMPLETE
        attempt = "".join(self.tiles[i] for i in self.current_attempt)
        if attempt != to_base_form(self.answer):
            return GuessResult.WRONG
        self.solved = True
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
        if self.done:
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

    def reveal(self) -> None:
        """Gives up on the word: fills the slots with the correct spelling
        and marks it done without counting it as solved."""
        if self.done:
            return
        unused = list(range(len(self.tiles)))
        attempt = []
        for letter in to_base_form(self.answer):
            match = next(i for i in unused if self.tiles[i] == letter)
            unused.remove(match)
            attempt.append(match)
        self.current_attempt = attempt
        self.revealed = True
