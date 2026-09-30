import random

from simon.models import COLORS
from simon.storage import new_session_id

MAX_SEQUENCE_LENGTH = 20
MISSES_ALLOWED_PER_LENGTH = 2  # a single wrong tap gives one visible retry at
# the same sequence (rehab-friendly: doesn't punish one slip as harshly as a
# genuine failure to recall); a second consecutive miss ends the session


class SimonSession:
    """Drives one Simon game session: grows a random color sequence one step
    at a time, and the player must replay it from memory each round.

    UI-independent and seedable so sequence generation is deterministically
    testable.
    """

    def __init__(
        self,
        start_length: int = 2,
        step_ms: int = 900,
        rng: random.Random | None = None,
    ) -> None:
        # stable id for the saved progress record (see storage.upsert_session)
        self.log_id = new_session_id()
        self._rng = rng or random.Random()
        self.step_ms = step_ms
        self.sequence: list[int] = [
            self._rng.randrange(len(COLORS)) for _ in range(max(1, start_length))
        ]
        self.best_length = 0
        self.rounds_played = 0
        self.rounds_correct = 0
        self._misses_at_current_length = 0
        self.finished = False

    @property
    def current_length(self) -> int:
        return len(self.sequence)

    def _grow_sequence(self) -> None:
        self.sequence.append(self._rng.randrange(len(COLORS)))
        self._misses_at_current_length = 0

    def record_round(self, correct: bool) -> None:
        """Call once per full-sequence attempt (the player replayed the
        whole sequence, right or wrong)."""
        if self.finished:
            raise RuntimeError("session already finished")
        self.rounds_played += 1
        if correct:
            self.rounds_correct += 1
            self.best_length = self.current_length
            if self.current_length >= MAX_SEQUENCE_LENGTH:
                self.finished = True
            else:
                self._grow_sequence()
        else:
            self._misses_at_current_length += 1
            if self._misses_at_current_length >= MISSES_ALLOWED_PER_LENGTH:
                self.finished = True

    @property
    def accuracy(self) -> float:
        return self.rounds_correct / self.rounds_played if self.rounds_played else 0.0
