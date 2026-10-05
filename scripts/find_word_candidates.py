"""Offline helper for growing the scrambled-words and change-a-word banks
deterministically from a real Hebrew dictionary. Not run at app runtime and
not unit tested (like generate_subword_bank.py).

Sources (downloaded into the git-ignored scripts/.cache):
- ויקימילון (Hebrew Wiktionary, CC BY-SA), parsed by hebrew_wiktionary.py:
  confirms a word exists and supplies its Hebrew definitions and topic
  categories;
- the FrequencyWords Hebrew list (OpenSubtitles): how common a word is,
  which decides its level -- regular for everyday words, advanced for
  less common ones. Words missing from the list are too rare to use.

Reports (in scripts/.cache):
- anagram_candidates.txt: groups of 2+ dictionary words spelled with the
  same letters, not yet in any change-a-word bank, by level;
- category_candidates.txt: dictionary words per topic category, not yet in
  the scrambled-words bank, by level.
Each candidate is listed with its frequency rank and dictionary
definition, so clues are written from the dictionary's meaning.

Usage:
    python scripts/find_word_candidates.py            # write both reports
    python scripts/find_word_candidates.py --check    # list bank words the dictionary doesn't confirm
"""

import argparse
import collections
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hebrew_wiktionary import load_lookup  # noqa: E402
from simon.hebrew_letters import FINAL_TO_BASE, to_base_form  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "simon" / "data"
FREQ_URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/he/he_50k.txt"

MIN_LEN, MAX_LEN = 3, 6
# frequency rank (1 = most common) at which a word moves from regular to advanced
REGULAR_MAX_RANK = 12000
ADVANCED_MAX_RANK = 50000


def load_frequency_ranks() -> dict[str, int]:
    path = CACHE_DIR / "he_50k.txt"
    if not path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FREQ_URL, path)
    ranks = {}
    for rank, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        ranks.setdefault(line.split(" ")[0], rank)
    return ranks


def level_for(rank: int | None) -> str | None:
    if rank is None or rank > ADVANCED_MAX_RANK:
        return None
    return "regular" if rank <= REGULAR_MAX_RANK else "advanced"


def is_playable(word: str) -> bool:
    return MIN_LEN <= len(word) <= MAX_LEN and not set(word[:-1]) & set(FINAL_TO_BASE) and len(set(word)) >= 2


def bank_words() -> tuple[dict[str, set[str]], set[str]]:
    """(topic -> words already in that topic at any level, words in any riddle pair)"""
    scramble = json.loads((DATA_DIR / "scramble_categories.json").read_text(encoding="utf-8"))
    topics = {name: set(info["words"]) | set(info.get("advanced", {})) for name, info in scramble.items()}
    pair_words = set()
    for name in ("change_word_pairs.json", "change_word_pairs_advanced.json"):
        for pair in json.loads((DATA_DIR / name).read_text(encoding="utf-8")):
            pair_words.update(entry["word"] for entry in pair)
    return topics, pair_words


def _describe(word: str, lookup, ranks) -> str:
    definition = lookup[word]["definitions"][0][:110]
    return f"{word} (#{ranks[word]}: {definition})"


def write_anagram_report(lookup, ranks, used: set[str]) -> int:
    groups = collections.defaultdict(list)
    for word in lookup:
        if is_playable(word) and word not in used and level_for(ranks.get(word)):
            groups["".join(sorted(to_base_form(word)))].append(word)
    found = {"regular": [], "advanced": []}
    for words in groups.values():
        if len(words) >= 2:
            words.sort(key=lambda w: ranks[w])
            found[level_for(max(ranks[w] for w in words))].append(words)
    out = CACHE_DIR / "anagram_candidates.txt"
    with out.open("w", encoding="utf-8") as f:
        for level, groups_at_level in found.items():
            groups_at_level.sort(key=lambda ws: max(ranks[w] for w in ws))
            f.write(f"===== {level} ({len(groups_at_level)} groups)\n")
            for words in groups_at_level:
                f.write("  |  ".join(_describe(w, lookup, ranks) for w in words) + "\n")
    return sum(len(g) for g in found.values())


def write_category_report(lookup, ranks, topics: dict[str, set[str]]) -> int:
    in_any_topic = set().union(*topics.values())
    by_category = collections.defaultdict(list)
    for word, entry in lookup.items():
        if is_playable(word) and word not in in_any_topic and level_for(ranks.get(word)):
            for category in entry["categories"]:
                by_category[category].append(word)
    out = CACHE_DIR / "category_candidates.txt"
    total = 0
    with out.open("w", encoding="utf-8") as f:
        for category, words in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
            if len(words) < 3:
                continue
            words.sort(key=lambda w: ranks[w])
            total += len(words)
            f.write(f"== {category} ({len(words)})\n")
            for w in words:
                f.write(f"  [{level_for(ranks[w])}] {_describe(w, lookup, ranks)}\n")
    return total


def check_banks(lookup, ranks) -> None:
    topics, pair_words = bank_words()
    all_words = set().union(*topics.values()) | pair_words
    missing = sorted(w for w in all_words if w not in lookup)
    print(f"{len(all_words)} bank words; {len(all_words) - len(missing)} confirmed by ויקימילון")
    print(f"not in ויקימילון ({len(missing)}):", " ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="list bank words the dictionary doesn't confirm")
    args = parser.parse_args()
    lookup, ranks = load_lookup(), load_frequency_ranks()
    if args.check:
        check_banks(lookup, ranks)
        return
    topics, pair_words = bank_words()
    print(f"{write_anagram_report(lookup, ranks, pair_words)} anagram groups -> {CACHE_DIR / 'anagram_candidates.txt'}")
    print(f"{write_category_report(lookup, ranks, topics)} category words -> {CACHE_DIR / 'category_candidates.txt'}")


if __name__ == "__main__":
    main()
