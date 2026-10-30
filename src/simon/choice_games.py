"""The three multiple-choice word games. They share one engine
(ChoiceSession), one progress store class and one pair of screens; this
registry is what tells them apart."""

from dataclasses import dataclass

from simon.choice_bank import ChoiceItem, definition_items, load_relation_items
from simon.word_levels import LEVELS


@dataclass(frozen=True)
class ChoiceGame:
    key: str
    title: str
    subtitle: str
    prompt_line: str  # the question above the prompt card
    route: str
    theme_key: str


CHOICE_GAMES = {
    game.key: game
    for game in (
        ChoiceGame("synonym", "מילה נרדפת", "מצאו מילה עם אותה משמעות", "איזו מילה אומרת אותו דבר?", "/synonym", "synonym"),
        ChoiceGame("opposite", "הפכים", "מצאו את ההפך", "מה ההפך של המילה?", "/opposite", "opposite"),
        ChoiceGame("definition", "מה המילה?", "התאימו מילה להגדרה", "איזו מילה מתאימה להגדרה?", "/definition", "definition"),
    )
}


def load_choice_items(scramble_categories: dict) -> dict[str, dict[str, list[ChoiceItem]]]:
    """game key -> word level -> that game's questions."""
    return {
        "synonym": {level: load_relation_items("synonyms", level) for level in LEVELS},
        "opposite": {level: load_relation_items("opposites", level) for level in LEVELS},
        "definition": {level: definition_items(scramble_categories, level) for level in LEVELS},
    }
