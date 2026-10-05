"""Parses the Hebrew Wiktionary (ויקימילון) dump into a word lookup with
Hebrew definitions and topic categories. Offline tooling only -- not used
at app runtime, and the dump itself stays in the git-ignored scripts/.cache.

Source and license: ויקימילון, https://he.wiktionary.org, CC BY-SA. Clues
in the app that are adapted from its definitions must keep attribution
(see README).

Entries are keyed by their full spelling (כתיב מלא, as the app writes
words: שולחן, not the dictionary's page title שלחן), without niqqud.

Usage (builds and caches scripts/.cache/hewiktionary.json):
    python scripts/hebrew_wiktionary.py
"""

import bz2
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
DUMP_URL = "https://dumps.wikimedia.org/hewiktionary/latest/hewiktionary-latest-pages-articles.xml.bz2"
DUMP_PATH = CACHE_DIR / "hewiktionary.xml.bz2"
LOOKUP_PATH = CACHE_DIR / "hewiktionary.json"

HEBREW_LETTERS = set("אבגדהוזחטיכלמנסעפצקרשתךםןףץ")

_PAGE = re.compile(r"<page>(.*?)</page>", re.S)
_TITLE = re.compile(r"<title>(.*?)</title>")
_TEXT = re.compile(r"<text[^>]*>(.*?)</text>", re.S)
_ENTRY_HEADER = re.compile(r"^==([^=].*?)==\s*$", re.M)
_FULL_SPELLING = re.compile(r"\|\s*כתיב מלא\s*=\s*([^\n|}]*)")
_POS = re.compile(r"\|\s*חלק דיבר\s*=\s*([^\n|}]*)")
_CATEGORY = re.compile(r"\[\[קטגוריה:([^\]|]+)")
_DEFINITION = re.compile(r"^#(?![:*#])\s*(.+)$", re.M)


def strip_niqqud(text: str) -> str:
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _unescape(text: str) -> str:
    return text.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def clean_wikitext(text: str) -> str:
    """Turns a definition line's wikitext into plain Hebrew text."""
    text = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    # templates, innermost first (they nest); usage labels like {{רובד|מקרא}} are dropped
    for _ in range(5):
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)  # [[target|label]] -> label
    text = text.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", text).strip(" ;,.")


def _is_playable(word: str) -> bool:
    return bool(word) and all(ch in HEBREW_LETTERS for ch in word)


def parse_dump(path: Path) -> dict[str, dict]:
    """word -> {"pos": [...], "definitions": [...], "categories": [...]}"""
    raw = bz2.open(path, "rt", encoding="utf-8").read()
    lookup: dict[str, dict] = {}
    for page in _PAGE.findall(raw):
        if "<ns>0</ns>" not in page or "<redirect" in page:
            continue
        title = _unescape(_TITLE.search(page).group(1))
        text_match = _TEXT.search(page)
        if not text_match:
            continue
        text = _unescape(text_match.group(1))
        categories = sorted(set(_CATEGORY.findall(text)))
        headers = list(_ENTRY_HEADER.finditer(text))
        for i, header in enumerate(headers):
            body = text[header.end(): headers[i + 1].start() if i + 1 < len(headers) else len(text)]
            full = _FULL_SPELLING.search(body)
            word = strip_niqqud((full.group(1) if full and full.group(1).strip() else title)).strip()
            word = word.split(",")[0].strip()  # some list two full spellings
            if not _is_playable(word):
                continue
            definitions = [d for d in (clean_wikitext(line) for line in _DEFINITION.findall(body)) if len(d) > 2]
            if not definitions:
                continue
            entry = lookup.setdefault(word, {"pos": [], "definitions": [], "categories": []})
            pos = _POS.search(body)
            if pos and pos.group(1).strip() not in entry["pos"]:
                entry["pos"].append(pos.group(1).strip())
            entry["definitions"].extend(d for d in definitions if d not in entry["definitions"])
            entry["categories"] = sorted(set(entry["categories"]) | set(categories))
    return lookup


def load_lookup() -> dict[str, dict]:
    """The parsed lookup, building (and downloading the dump) on first use."""
    if not LOOKUP_PATH.exists():
        if not DUMP_PATH.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            print(f"Downloading {DUMP_URL}")
            urllib.request.urlretrieve(DUMP_URL, DUMP_PATH)
        LOOKUP_PATH.write_text(json.dumps(parse_dump(DUMP_PATH), ensure_ascii=False), encoding="utf-8")
    return json.loads(LOOKUP_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    lookup = load_lookup()
    print(f"{len(lookup)} words with Hebrew definitions -> {LOOKUP_PATH}")
    for word in sys.argv[1:] or ["שולחן", "שמיר", "תבונה", "רופא", "אפור"]:
        entry = lookup.get(word)
        print(word, "->", entry["definitions"][:2] if entry else "NOT FOUND", entry["categories"][:4] if entry else "")
