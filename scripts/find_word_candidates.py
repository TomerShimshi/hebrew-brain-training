"""One-off, offline helper for growing the scrambled-words and change-a-word
banks. Not run at app runtime and not unit tested (like
generate_subword_bank.py).

It only *suggests* candidates -- a person still picks the familiar ones and
writes the Hebrew clues, since the dictionary only has English glosses and
clues for this audience need a human touch. Two sources, both downloaded
into scripts/.cache/ (git-ignored):

- kaikki.org's Hebrew Wiktionary extract: confirms a word is a real
  dictionary entry, and supplies English glosses and topic categories;
- the FrequencyWords Hebrew list (OpenSubtitles): ranks how common a word
  is, so rare or archaic entries can be filtered out.

Writes two reports:
- anagram_candidates.txt: groups of 2+ common words spelled with the same
  letters (candidate change-a-word pairs), skipping words already used;
- category_candidates.txt: common words per Wiktionary topic category
  (candidate scrambled-words entries), skipping words already used.

Usage:
    python scripts/find_word_candidates.py [--max-rank 20000]
"""

import argparse
import collections
import json
import sys
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from simon.hebrew_letters import to_base_form  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "simon" / "data"
KAIKKI_URL = "https://kaikki.org/dictionary/Hebrew/kaikki.org-dictionary-Hebrew.jsonl"
FREQ_URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/he/he_50k.txt"

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשתךםןףץ")
FINAL_LETTERS = set("ךםןףץ")
POS = {"noun", "adj", "verb", "adv", "num"}
MIN_LEN, MAX_LEN = 3, 6

# Wiktionary topic categories worth mining for the scrambled-words game.
CATEGORIES = [
    "Fruits", "Vegetables", "Foods", "Breads", "Anatomy", "Face", "Hair",
    "Occupations", "Clothing", "Headwear", "Tools", "Furniture", "Rooms",
    "Buildings", "Containers", "Vehicles", "Watercraft", "Birds",
    "Baby animals", "Trees", "Flowers", "Plants", "Colors", "Landforms",
    "Bodies of water", "Sports", "Music", "Holidays", "Time", "Months",
    "Light sources", "Liquids", "Weather", "Male family members",
    "Female family members",
]


def _fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)
    return dest


def _is_playable(word: str) -> bool:
    return (
        MIN_LEN <= len(word) <= MAX_LEN
        and all(ch in HEBREW_LETTERS for ch in word)
        and not set(word[:-1]) & FINAL_LETTERS
    )


def load_frequency_ranks(path: Path) -> dict[str, int]:
    ranks = {}
    for rank, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        word = line.split(" ")[0]
        ranks.setdefault(word, rank)
    return ranks


def load_dictionary(path: Path) -> dict[str, dict]:
    """word -> {"glosses": [...], "categories": {...}} for playable,
    single-word entries of the parts of speech in POS."""
    entries: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            word = "".join(ch for ch in e.get("word", "") if not unicodedata.combining(ch))
            if e.get("pos") not in POS or not _is_playable(word):
                continue
            entry = entries.setdefault(word, {"glosses": [], "categories": set()})
            for sense in e.get("senses", []):
                entry["glosses"].extend(sense.get("glosses", [])[:1])
                for c in sense.get("categories", []):
                    if isinstance(c, dict):
                        entry["categories"].add(c["name"])
    return entries


def used_words() -> tuple[set[str], set[str]]:
    scramble = json.loads((DATA_DIR / "scramble_categories.json").read_text(encoding="utf-8"))
    pairs = json.loads((DATA_DIR / "change_word_pairs.json").read_text(encoding="utf-8"))
    scramble_words = {w for info in scramble.values() for w in info["words"]}
    pair_words = {entry["word"] for pair in pairs for entry in pair}
    return scramble_words, pair_words


def _gloss(entry: dict) -> str:
    return "; ".join(dict.fromkeys(entry["glosses"]))[:90]


def write_anagram_report(dictionary, ranks, max_rank, exclude, out: Path) -> int:
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for word in dictionary:
        if ranks.get(word, 10**9) <= max_rank and word not in exclude:
            groups["".join(sorted(to_base_form(word)))].append(word)
    found = [sorted(ws, key=lambda w: ranks[w]) for ws in groups.values() if len(ws) >= 2]
    # most familiar first: rank a group by its *least* common member
    found.sort(key=lambda ws: max(ranks[w] for w in ws))
    with out.open("w", encoding="utf-8") as f:
        for ws in found:
            f.write("  |  ".join(f"{w} (#{ranks[w]}: {_gloss(dictionary[w])})" for w in ws) + "\n")
    return len(found)


def write_category_report(dictionary, ranks, max_rank, exclude, out: Path) -> int:
    total = 0
    with out.open("w", encoding="utf-8") as f:
        for category in CATEGORIES:
            words = [
                w for w, e in dictionary.items()
                if category in e["categories"] and ranks.get(w, 10**9) <= max_rank and w not in exclude
            ]
            words.sort(key=lambda w: ranks[w])
            total += len(words)
            f.write(f"== {category} ({len(words)})\n")
            for w in words:
                f.write(f"  {w} (#{ranks[w]}: {_gloss(dictionary[w])})\n")
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-rank", type=int, default=20000,
                        help="only words within this frequency rank (lower = more common)")
    args = parser.parse_args()

    ranks = load_frequency_ranks(_fetch(FREQ_URL, CACHE_DIR / "he_50k.txt"))
    dictionary = load_dictionary(_fetch(KAIKKI_URL, CACHE_DIR / "kaikki_he_raw.jsonl"))
    scramble_words, pair_words = used_words()

    n = write_anagram_report(dictionary, ranks, args.max_rank, pair_words, CACHE_DIR / "anagram_candidates.txt")
    print(f"{n} anagram groups -> {CACHE_DIR / 'anagram_candidates.txt'}")
    n = write_category_report(dictionary, ranks, args.max_rank, scramble_words, CACHE_DIR / "category_candidates.txt")
    print(f"{n} category words -> {CACHE_DIR / 'category_candidates.txt'}")


if __name__ == "__main__":
    main()
