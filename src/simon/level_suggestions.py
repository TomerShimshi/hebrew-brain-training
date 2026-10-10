"""When to suggest changing the word level (see word_levels).

The player always decides: a suggestion is only an offer, shown after a
finished word (never mid-word), and declining is respected -- no more
offers for the rest of that game, and after two declines within a week the
offers pause for a week (see SettingsStore).

- Up (regular -> advanced): after a run of clean solves in a row.
- Down (advanced -> regular): when several recent words were a struggle.
  Framed as "for now", never as failure.
"""

import enum
from dataclasses import dataclass

from simon.word_levels import ADVANCED, REGULAR


class Outcome(enum.Enum):
    CLEAN = "clean"  # solved without letter hints or revealing
    OK = "ok"  # solved with a little help
    STRUGGLE = "struggle"  # revealed, or needed several letter hints


class Suggestion(enum.Enum):
    UP = "up"
    DOWN = "down"

    @property
    def target_level(self) -> str:
        return ADVANCED if self is Suggestion.UP else REGULAR


@dataclass(frozen=True)
class Thresholds:
    up_streak: int  # clean outcomes in a row before suggesting advanced
    down_window: int  # how many recent outcomes to look at for "too hard"
    down_struggles: int  # struggles within that window before suggesting regular


SCRAMBLE = Thresholds(up_streak=8, down_window=4, down_struggles=3)
CHANGE_WORD = Thresholds(up_streak=5, down_window=3, down_struggles=2)

# letter hints on one word that make it count as a struggle
STRUGGLE_HINTS = 2


def classify(puzzle) -> Outcome:
    """A finished puzzle's outcome. Definition clues don't count as help --
    understanding the meaning is the point; letter hints and revealing do."""
    if puzzle.revealed or puzzle.hints_used >= STRUGGLE_HINTS:
        return Outcome.STRUGGLE
    return Outcome.CLEAN if puzzle.hints_used == 0 else Outcome.OK


def worst(*outcomes: Outcome) -> Outcome:
    if Outcome.STRUGGLE in outcomes:
        return Outcome.STRUGGLE
    return Outcome.OK if Outcome.OK in outcomes else Outcome.CLEAN


def clean_streak(outcomes: list[Outcome]) -> int:
    streak = 0
    for outcome in reversed(outcomes):
        if outcome is not Outcome.CLEAN:
            break
        streak += 1
    return streak


def suggest(level: str, outcomes: list[Outcome], thresholds: Thresholds) -> Suggestion | None:
    if level == REGULAR:
        return Suggestion.UP if clean_streak(outcomes) >= thresholds.up_streak else None
    recent = outcomes[-thresholds.down_window:]
    struggles = sum(outcome is Outcome.STRUGGLE for outcome in recent)
    return Suggestion.DOWN if struggles >= thresholds.down_struggles else None
