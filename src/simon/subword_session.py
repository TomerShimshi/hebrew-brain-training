import enum
import random

from simon.freshness import freshness_order
from simon.hebrew_letters import to_base_form, to_display_form
from simon.storage import new_session_id

MIN_ATTEMPT_LENGTH = 2


class CheckResult(enum.Enum):
    TOO_SHORT = "too_short"
    ALREADY_FOUND = "already_found"
    NOT_A_WORD = "not_a_word"
    FOUND = "found"


def choose_base_word(
    bank: dict[str, list[str]],
    rng: random.Random,
    exclude: str | None = None,
    seen_history: list[list[str]] | None = None,
) -> str:
    """Picks the base word the player has gone longest without seeing
    (never-seen words first; see freshness_order), skipping `exclude`
    unless it's the only word in the bank."""
    choices = [w for w in bank if w != exclude] or list(bank)
    return freshness_order(choices, seen_history or [], rng)[0]


class SubWordSession:
    """Drives one word-building session: shows a base word as letter tiles,
    the player taps tiles (any order, any subset) to build other real
    Hebrew words hidden inside it, checked against a precomputed bank of
    valid sub-words for that base word.

    UI-independent and seedable so base-word selection is deterministically
    testable. `bank` and `clues` are injected so tests can use small
    fixtures instead of the full curated dataset.
    """

    def __init__(
        self,
        bank: dict[str, list[str]],
        clues: dict[str, str],
        rng: random.Random | None = None,
        base_word: str | None = None,
        seen_history: list[list[str]] | None = None,
    ) -> None:
        """`seen_history` is the player's past games' base words, oldest
        first, so new games favour base words they haven't met yet."""
        # stable id for the saved progress record (see storage.upsert_session)
        self.log_id = new_session_id()
        self._bank = bank
        self._clues = clues
        self._rng = rng or random.Random()
        self._seen_history = seen_history or []
        self.base_words_shown: list[str] = []
        self.total_found_count = 0
        self.hints_used = 0
        self._pending_clue_word: str | None = None
        self.current_attempt: list[int] = []
        self.found_words: list[str] = []
        self._set_base_word(base_word or choose_base_word(bank, self._rng, seen_history=self._seen_history))

    def _set_base_word(self, base_word: str) -> None:
        self.base_word = base_word
        self.tiles: list[str] = list(base_word)
        self.current_attempt = []
        self.found_words = []
        self._pending_clue_word = None
        self.base_words_shown.append(base_word)

    @property
    def valid_subwords(self) -> list[str]:
        return self._bank[self.base_word]

    def _remaining_words(self) -> list[str]:
        return [w for w in self.valid_subwords if w not in self.found_words]

    def tap_tile(self, index: int) -> None:
        if index not in self.current_attempt:
            self.current_attempt.append(index)

    def undo_last(self) -> None:
        if self.current_attempt:
            self.current_attempt.pop()

    def clear_attempt(self) -> None:
        self.current_attempt = []

    def current_attempt_display(self) -> str:
        return "".join(self.tiles[i] for i in self.current_attempt)

    def check_attempt(self) -> CheckResult:
        if len(self.current_attempt) < MIN_ATTEMPT_LENGTH:
            return CheckResult.TOO_SHORT

        key = to_base_form(self.current_attempt_display())
        display = to_display_form(key)

        if display in self.found_words:
            return CheckResult.ALREADY_FOUND

        valid_keys = {to_base_form(w) for w in self.valid_subwords}
        if key not in valid_keys:
            return CheckResult.NOT_A_WORD

        self.found_words.append(display)
        self.total_found_count += 1
        if display == self._pending_clue_word:
            self._pending_clue_word = None
        self.clear_attempt()
        return CheckResult.FOUND

    def get_clue(self) -> str | None:
        """Returns a clue (definition) for one not-yet-found valid word,
        without revealing the word itself -- the player can keep trying to
        build it. Returns the same clue on repeated calls until that word
        is found or revealed, so pressing the button again doesn't shuffle
        to a different word mid-attempt. Returns None once every word has
        been found."""
        if self._pending_clue_word is None:
            remaining = self._remaining_words()
            if not remaining:
                return None
            self._pending_clue_word = self._rng.choice(remaining)
        return self._clues[self._pending_clue_word]

    def reveal_word(self) -> str | None:
        """Reveals a word outright: the one a pending clue was about, if
        any, otherwise a random not-yet-found word. Counts as a hint used.
        Returns None once every word has been found."""
        word = self._pending_clue_word
        if word is None:
            remaining = self._remaining_words()
            if not remaining:
                return None
            word = self._rng.choice(remaining)

        self.found_words.append(word)
        self.total_found_count += 1
        self.hints_used += 1
        self._pending_clue_word = None
        return word

    def new_base_word(self) -> None:
        # this game's own base words count as the most recently seen
        history = self._seen_history + [self.base_words_shown]
        self._set_base_word(choose_base_word(self._bank, self._rng, exclude=self.base_word, seen_history=history))
