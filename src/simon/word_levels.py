"""Word levels for the word games (scrambled words, change-a-word).

- regular: everyday words -- comfortable practice;
- advanced: richer, less common words, each with a definition that teaches
  its meaning -- for learning new vocabulary.

The player picks the level on the home screen; it's remembered per profile
(see settings_storage)."""

REGULAR = "regular"
ADVANCED = "advanced"
LEVELS = (REGULAR, ADVANCED)
LABELS = {REGULAR: "רגיל", ADVANCED: "מתקדם"}


def topic_words(topic: dict, level: str) -> dict[str, str]:
    """A scrambled-words topic's {word: clue} at the given level. Advanced
    words live under the topic's optional "advanced" key."""
    return topic.get("advanced", {}) if level == ADVANCED else topic["words"]
