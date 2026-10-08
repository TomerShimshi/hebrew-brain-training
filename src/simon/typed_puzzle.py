from simon.hebrew_letters import to_base_form, to_display_form
from simon.letter_puzzle import GuessResult


class TypedPuzzle:
    """One word to type from memory on a full Hebrew keyboard -- unlike
    LetterPuzzle, no letters are handed to the player, so the word has to
    be recalled unaided (the change-a-word game's first stage).

    Letters are compared in non-final form, so typing מ or ם at the end
    of a word is equally correct. The answer's length is shown as slots,
    and typing stops once they're all filled.
    """

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self._target = to_base_form(answer)
        self.typed: list[str] = []
        self.solved = False
        self.revealed = False
        self.hints_used = 0

    @property
    def done(self) -> bool:
        return self.solved or self.revealed

    @property
    def length(self) -> int:
        return len(self._target)

    def type_letter(self, letter: str) -> None:
        if not self.done and len(self.typed) < self.length:
            self.typed.append(to_base_form(letter))

    def backspace(self) -> None:
        if not self.done and self.typed:
            self.typed.pop()

    def clear(self) -> None:
        if not self.done:
            self.typed = []

    def is_full(self) -> bool:
        return len(self.typed) == self.length

    def slot_letters(self) -> list[str]:
        """One entry per letter of the answer: the typed letter, or "" for
        a still-empty slot. The final-form substitution is applied only
        once every slot is filled."""
        placed = "".join(self.typed)
        if self.is_full():
            placed = to_display_form(placed)
        return list(placed) + [""] * (self.length - len(placed))

    def check_attempt(self) -> GuessResult:
        if self.done:
            return GuessResult.CORRECT
        if not self.is_full():
            return GuessResult.INCOMPLETE
        if "".join(self.typed) != self._target:
            return GuessResult.WRONG
        self.solved = True
        return GuessResult.CORRECT

    def hint_next_letter(self) -> bool:
        """Keeps the correctly-typed prefix, drops anything after it, and
        types the next correct letter. Counts as a hint. Returns False if
        the word is already done or fully spelled."""
        if self.done:
            return False
        keep = 0
        while keep < len(self.typed) and self.typed[keep] == self._target[keep]:
            keep += 1
        if keep == self.length:
            return False
        self.typed = self.typed[:keep] + [self._target[keep]]
        self.hints_used += 1
        return True

    def reveal(self) -> None:
        """Gives up on the word: fills in the answer and marks it done
        without counting it as solved."""
        if self.done:
            return
        self.typed = list(self._target)
        self.revealed = True
