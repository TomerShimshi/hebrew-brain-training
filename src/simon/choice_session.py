import random

from simon import level_suggestions
from simon.choice_bank import ChoiceItem
from simon.freshness import freshness_order
from simon.storage import new_session_id
from simon.word_levels import REGULAR

OPTION_COUNT = 4


class ChoiceSession:
    """Drives one game of a multiple-choice word game: `question_count`
    questions, unseen answers first (see freshness_order), each with four
    shuffled options. A wrong pick is greyed out and the question stays
    open until the right one is picked -- no penalty beyond the outcome.

    UI-independent and seedable so question order and options are
    deterministically testable.
    """

    def __init__(
        self,
        items: list[ChoiceItem],
        rng: random.Random | None = None,
        question_count: int = 10,
        seen_history: list[list[str]] | None = None,
        level: str = REGULAR,
    ) -> None:
        # stable id for the saved progress record (see storage.upsert_session)
        self.log_id = new_session_id()
        self.level = level
        self._items = items
        self._rng = rng or random.Random()
        by_answer: dict[str, list[ChoiceItem]] = {}
        for item in items:
            by_answer.setdefault(item.answer, []).append(item)
        # one question per answer, so a game never asks for the same word twice
        order = freshness_order(list(by_answer), seen_history or [], self._rng)[:question_count]
        self._queue = [self._rng.choice(by_answer[answer]) for answer in order]
        self._picks: list[list[str]] = []  # every pick, per question shown
        self.suggestion_dismissed = False
        self._advance()

    def _advance(self) -> None:
        self.item = self._queue[len(self._picks)]
        self._picks.append([])
        self.options = self._distractors(self.item) + [self.item.answer]
        self._rng.shuffle(self.options)

    def _distractors(self, item: ChoiceItem) -> list[str]:
        excluded = {item.prompt, item.answer} | item.related

        def pool(candidates) -> list[str]:
            return sorted({other.answer for other in candidates} - excluded)

        same_group = pool(o for o in self._items if item.group and o.group == item.group)
        picked = self._rng.sample(same_group, min(OPTION_COUNT - 1, len(same_group)))
        rest = [w for w in pool(self._items) if w not in picked]
        return picked + self._rng.sample(rest, min(OPTION_COUNT - 1 - len(picked), len(rest)))

    @property
    def picked(self) -> set[str]:
        return set(self._picks[-1])

    @property
    def done(self) -> bool:
        return self.item.answer in self._picks[-1]

    def pick(self, option: str) -> bool:
        """True when `option` is the answer. Picks after the question is
        answered are ignored."""
        if self.done:
            return False
        if option not in self._picks[-1]:
            self._picks[-1].append(option)
        return option == self.item.answer

    @property
    def total(self) -> int:
        return len(self._queue)

    @property
    def position(self) -> int:
        """1-based index of the current question."""
        return len(self._picks)

    @property
    def has_next(self) -> bool:
        return len(self._picks) < len(self._queue)

    def next_question(self) -> None:
        if self.has_next:
            self._advance()

    @property
    def answers_shown(self) -> list[str]:
        return [item.answer for item in self._queue[: len(self._picks)]]

    @property
    def outcomes(self) -> list[level_suggestions.Outcome]:
        """How each answered question went: right on the first pick, the
        second, or later (see level_suggestions)."""
        result = []
        for item, picks in zip(self._queue, self._picks):
            if item.answer in picks:
                tries = picks.index(item.answer) + 1
                result.append(
                    level_suggestions.Outcome.CLEAN if tries == 1
                    else level_suggestions.Outcome.OK if tries == 2
                    else level_suggestions.Outcome.STRUGGLE
                )
        return result

    @property
    def answered(self) -> int:
        return len(self.outcomes)

    @property
    def first_try_correct(self) -> int:
        return self.outcomes.count(level_suggestions.Outcome.CLEAN)

    @property
    def clean_streak(self) -> int:
        return level_suggestions.clean_streak(self.outcomes)

    def level_suggestion(self) -> level_suggestions.Suggestion | None:
        """Whether to offer a change of level now -- nothing once the player
        said "not now" in this game."""
        if self.suggestion_dismissed:
            return None
        return level_suggestions.suggest(self.level, self.outcomes, level_suggestions.CHOICE)
