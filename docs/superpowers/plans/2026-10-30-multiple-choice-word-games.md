# Multiple-Choice Word Games Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three multiple-choice word games — pick the **synonym** (מילה נרדפת), the **opposite** (הפך, e.g. חם → קר), or the **word matching a definition** — each from 4 options.

**Architecture:** The three games share one engine: a question is a prompt + 4 options (1 answer, 3 distractors), so one `ChoiceSession`, one progress store class, and one screen serve all three, configured by a small `ChoiceGame` registry entry per game. Synonym/opposite pairs come deterministically from ויקימילון's `מילים נרדפות` / `ניגודים` sections (via the existing offline pipeline); the definition game reuses the scrambled-words topic clues, so it needs no new content. The games plug into everything existing word games have: word levels, level suggestions, unseen-first, per-answer saving, public mode, progress chart.

**Tech Stack:** Python 3.12, Flet 0.86, pytest; offline scripts in `scripts/` using `scripts/.cache` (git-ignored).

**Spec:** the user's request of 2026-10-30, restated as Requirements below (no separate spec doc).

## Requirements (from the request)

1. **מילה נרדפת** — show a word; pick its synonym out of 4 options.
2. **הפכים** — show a word; pick its opposite (חם → קר) out of 4 options.
3. **מה המילה?** — show a definition; pick the word it defines out of 4 options.

## Global Constraints

- Audience: a stroke survivor with word-finding difficulty — Hebrew UI, big touch targets, gentle non-punitive feedback (a wrong pick never ends a question; the player tries again).
- Must fit a 360×640 phone without horizontal overflow (see `content_width` / `game_header` in `src/simon/ui_helpers.py`).
- Words in banks: Hebrew letters only, single words, final letters only at word end (same checks as `tests/test_scramble_bank.py`).
- Every bank word must exist in ויקימילון; every synonym/opposite pair must be listed as such by ויקימילון (determinism — see memory "Hebrew dictionary pipeline" and README "Word banks and sources"). Keep the CC BY-SA attribution.
- Public mode (`APP_MODE=public`) must keep working: no persistence beyond the visit, no history UI (`state.public`).
- Word level (`state.word_level`, `simon/word_levels.py`) applies to all three games; level suggestions (`simon/level_suggestions.py`) apply too.
- Progress is saved after every answered question (`simon.storage.upsert_session` pattern).
- Questions per game: **10**. Options per question: **4**, shuffled.
- Commits stay local; push only after the user approves (project practice).

## Review Focus

- **Ambiguous options:** a distractor that is *also* a synonym/opposite of the prompt (e.g. both "גדול" and "ענק" offered for "עצום"). Expect: never happens — distractors exclude every word the dictionary relates to the prompt. Test in Task 3.
- **Duplicate option text:** the answer appearing twice, or two identical distractors. Expect 4 distinct options. Test in Task 3.
- **Small distractor pool:** a definition-game topic (or a level) with fewer than 4 usable words. Expect distractors to fall back to other topics/the whole bank, never fewer than 4 options and never a crash. Test in Task 3.
- **Long options on a narrow phone:** a long word or definition wraps; 4 option buttons must stay inside 360px and tappable. Screenshot check in Task 6.
- **Leaving mid-game:** progress so far is saved and nothing keeps running. Test in Task 4 (save per answer); the screen has no background tasks (verify in Task 6).

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/hebrew_wiktionary.py` (modify) | also parse `מילים נרדפות`/`נרדפות` → `synonyms`, `ניגודים`/`הפכים` → `opposites` per word |
| `scripts/find_word_candidates.py` (modify) | `--relations` report: candidate synonym/opposite pairs with levels and definitions |
| `scripts/import_dictionary_relations.py` (create) | validated import of hand-picked pairs into the relation banks |
| `src/simon/data/synonyms.json`, `opposites.json` (create) | `[{"word", "answer", "level", "related"}]` — `related`: every dictionary synonym/opposite of `word`, for distractor exclusion |
| `src/simon/choice_bank.py` (create) | `ChoiceItem`, loaders for the three games' items per level |
| `src/simon/choice_session.py` (create) | `ChoiceSession`: questions, options, answering, outcomes, level suggestion |
| `src/simon/choice_storage.py` (create) | `ChoiceProgressStore` (one class, keyed per game) |
| `src/simon/choice_games.py` (create) | `ChoiceGame` registry: key, Hebrew title/subtitle/prompt line, route, theme |
| `src/simon/screens/choice_game.py`, `choice_summary.py` (create) | the shared game and summary screens |
| `src/simon/app_state.py`, `main.py`, `ui_helpers.py`, `screens/home.py`, `screens/progress_view.py`, `level_suggestions.py` (modify) | wiring |

---

### Task 1: Dictionary relations — parse, report, validated import

**Files:**
- Modify: `scripts/hebrew_wiktionary.py`, `scripts/find_word_candidates.py`
- Create: `scripts/import_dictionary_relations.py`

**Interfaces:**
- Produces: lookup entries gain `"synonyms": list[str]` and `"opposites": list[str]` (full spelling, no niqqud, single Hebrew words only; multi-word links dropped). `python scripts/find_word_candidates.py --relations` writes `scripts/.cache/relation_candidates.txt`. `python scripts/import_dictionary_relations.py FILE` where FILE is `{"synonyms": [[word, answer], ...], "opposites": [[word, answer], ...]}`; refuses a pair unless both words are in the lookup, the dictionary lists the relation in either direction, and both are single Hebrew words; sets `"level"` = `level_for(max(rank(word), rank(answer)), allow_rare=True)`; sets `"related"` = union of both words' dictionary synonyms+opposites (plus each other); appends to `src/simon/data/synonyms.json` / `opposites.json` (one entry per line), refusing duplicates of an existing `word`.

(Offline tooling — not unit tested, per the `scripts/` convention.)

- [ ] **Step 1:** In `parse_dump`, collect `[[target]]`/`[[target|label]]` link targets under the `===מילים נרדפות===`/`===נרדפות===` and `===ניגודים===`/`===הפכים===` subsections of each entry body; delete `scripts/.cache/hewiktionary.json` so it rebuilds.
- [ ] **Step 2:** Verify: `python scripts/hebrew_wiktionary.py חם גדול` prints entries whose `opposites` include `קר` and `קטן` respectively (spot-check; if not, fix the section regex).
- [ ] **Step 3:** Add `--relations` to `find_word_candidates.py`: pairs where both words are playable dictionary words with a level (strict `level_for`), grouped by level, each line `word → answer (#rank: definition)`, archaic categories excluded as in the topic report.
- [ ] **Step 4:** Write `import_dictionary_relations.py` per the Interfaces block.
- [ ] **Step 5:** Verify the guard: import a file with one bogus pair (`["חם", "שולחן"]`) → exits non-zero with "not listed by ויקימילון".
- [ ] **Step 6: Commit** — `git add scripts/ && git commit -m "Parse synonyms/opposites from ויקימילון and add validated relation import"`

### Task 2: Synonym and opposite banks (content)

**Files:**
- Create: `src/simon/data/synonyms.json`, `src/simon/data/opposites.json` (via the Task 1 import)
- Test: `tests/test_choice_banks.py`

**Interfaces:**
- Consumes: Task 1 import script.
- Produces: banks with ≥ **40 regular and ≥ 30 advanced** entries each; entry shape `{"word": str, "answer": str, "level": "regular"|"advanced", "related": list[str]}`.

- [ ] **Step 1: Write the failing test** `tests/test_choice_banks.py`:

```python
@pytest.mark.parametrize("name", ["synonyms", "opposites"])
@pytest.mark.parametrize("level,minimum", [("regular", 40), ("advanced", 30)])
def test_bank_has_enough_entries(name, level, minimum): ...
def test_entries_are_single_hebrew_words(name): ...       # HEBREW_LETTERS, finals only at end, len 2..8
def test_no_word_repeats_within_a_bank(name): ...
def test_answer_is_in_related_and_word_is_not(name): ...  # answer in related; word not in related
```

- [ ] **Step 2:** Run `pytest tests/test_choice_banks.py -v` → FAIL (files missing).
- [ ] **Step 3:** Run `--relations`, hand-pick familiar pairs (skip grammatical forms, slang, crude/violent words; each `word` once per bank), import them.
- [ ] **Step 4:** Run `pytest tests/test_choice_banks.py -v` → PASS.
- [ ] **Step 5: Commit** — `git add src/simon/data/synonyms.json src/simon/data/opposites.json tests/test_choice_banks.py && git commit -m "Add synonym and opposite banks from ויקימילון"`

### Task 3: Choice engine — items and session

**Files:**
- Create: `src/simon/choice_bank.py`, `src/simon/choice_session.py`
- Modify: `src/simon/level_suggestions.py` (add `CHOICE = Thresholds(up_streak=8, down_window=4, down_struggles=3)`)
- Test: `tests/test_choice_session.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class ChoiceItem: prompt: str; answer: str; group: str; related: frozenset[str]` — `group` = topic for the definition game, `""` otherwise.
  - `load_relation_items(kind: str, level: str) -> list[ChoiceItem]` (`kind` ∈ `"synonyms"`, `"opposites"`; prompt = `word`).
  - `definition_items(categories: dict, level: str) -> list[ChoiceItem]` — one item per scrambled-words word: prompt = its clue, answer = the word, group = topic name, related = `frozenset()`.
  - `class ChoiceSession(items: list[ChoiceItem], rng: random.Random | None = None, question_count: int = 10, seen_history: list[list[str]] | None = None, level: str = REGULAR)`, attributes/methods: `log_id`, `level`, `item: ChoiceItem` (current), `options: list[str]` (4, shuffled), `picked: set[str]`, `done: bool`, `position: int` (1-based), `total: int`, `has_next: bool`, `pick(option: str) -> bool` (True = correct; wrong picks are remembered, question stays open; picks after `done` are ignored), `next_question() -> None`, `answers_shown: list[str]` (answers of the questions shown so far — the history unit for unseen-first), `first_try_correct: int`, `outcomes: list[Outcome]`, `clean_streak: int`, `suggestion_dismissed: bool`, `level_suggestion() -> Suggestion | None` (uses `CHOICE`).
  - Outcome per finished question: correct on first pick → CLEAN, second → OK, third or later → STRUGGLE.

- [ ] **Step 1: Write the failing tests** `tests/test_choice_session.py` (small fixture items):

```python
def test_each_question_has_four_distinct_options_including_the_answer(): ...
def test_distractors_never_include_related_words(): ...          # item.related ∩ options == {answer} or ∅
def test_definition_distractors_come_from_the_same_topic_when_possible(): ...
def test_small_pool_falls_back_to_other_items_and_still_gives_four(): ...  # Review Focus
def test_wrong_pick_keeps_the_question_open_and_correct_pick_finishes_it(): ...
def test_picks_after_done_are_ignored(): ...
def test_outcomes_first_second_third_try(): ...                   # CLEAN, OK, STRUGGLE
def test_plays_question_count_items_unseen_first(): ...           # freshness_order on answers
def test_level_suggestion_up_after_eight_first_try_answers(): ...
```

- [ ] **Step 2:** Run `pytest tests/test_choice_session.py -v` → FAIL (module missing).
- [ ] **Step 3:** Implement. Distractors: candidates = answers of other items (definition game: same `group` first), minus `{item.prompt, item.answer} | item.related`, deduplicated; `rng.sample` 3, topping up from the whole bank when short. Question order: `freshness_order` over answers, take `question_count`.
- [ ] **Step 4:** Run `pytest tests/test_choice_session.py tests/test_level_suggestions.py -v` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "Add multiple-choice engine shared by the three new games"`

### Task 4: Progress storage

**Files:**
- Create: `src/simon/choice_storage.py`
- Test: `tests/test_choice_storage.py`

**Interfaces:**
- Produces: `ChoiceProgressStore(game_key: str, store: KeyValueStore | None = None)`; storage key `f"{game_key}_progress_v1"`; `save_session(session_id: str, answers_shown: list[str], first_try_correct: int, answered: int, level: str)`, `last_session()`, `recent_sessions(n=10)`, `seen_history() -> list[list[str]]`, `best_first_try_correct() -> int | None`.

- [ ] **Step 1: Write the failing tests:** `test_saving_same_session_updates_in_place`, `test_games_do_not_share_progress` (two keys, one backend), `test_seen_history_oldest_first`, `test_best_first_try_correct`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement with `upsert_session`. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** — `git commit -m "Add per-game progress store for choice games"`

### Task 5: Registry and wiring

**Files:**
- Create: `src/simon/choice_games.py`
- Modify: `src/simon/ui_helpers.py` (3 themes), `src/simon/app_state.py`, `main.py`, `src/simon/screens/home.py`, `src/simon/screens/progress_view.py`
- Test: `tests/test_choice_games.py`

**Interfaces:**
- Consumes: Tasks 3–4.
- Produces: `@dataclass(frozen=True) class ChoiceGame: key: str; title: str; subtitle: str; prompt_line: str; route: str; theme_key: str` and `CHOICE_GAMES: dict[str, ChoiceGame]` with exactly:

| key | title | subtitle | prompt_line | route | theme (accent, light, icon) |
|---|---|---|---|---|---|
| `synonym` | מילה נרדפת | מצאו מילה עם אותה משמעות | איזו מילה אומרת אותו דבר? | `/synonym` | `#1098AD`, `#E3F7FA`, `\U0001f91d` |
| `opposite` | הפכים | מצאו את ההפך | מה ההפך של המילה? | `/opposite` | `#F08C00`, `#FFF4E0`, `↔️` |
| `definition` | מה המילה? | התאימו מילה להגדרה | איזו מילה מתאימה להגדרה? | `/definition` | `#5C940D`, `#EEF7E0`, `\U0001f4d6` |

  `AppState` gains `choice_items: dict[str, dict[str, list[ChoiceItem]]]` (game → level → items, loaded in `main`), `choice_progress: dict[str, ChoiceProgressStore]` (built in `_attach_stores`), `choice_sessions: dict[str, ChoiceSession | None]`. Routes `/<key>` and `/<key>/summary` registered in `ROUTE_BUILDERS` via the Task 6 builders. Home: one card per game after שינוי מילים, caption from last session (`בפעם הקודמת: {first_try_correct} מתוך {answered}`), hidden in public mode like the others. Progress view: one trend card per game on `first_try_correct`, higher is better.

- [ ] **Step 1: Write the failing tests:** `test_registry_has_the_three_games`, `test_every_game_has_items_at_both_levels` (≥ 10 each — enough for one game), `test_routes_are_registered` (import `main`, check both routes per game), `test_public_mode_keeps_choice_progress_in_memory` (extend the `tests/test_public_mode.py` pattern).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run full `pytest -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "Register the three choice games and wire them into the app"`

### Task 6: Game and summary screens

**Files:**
- Create: `src/simon/screens/choice_game.py`, `src/simon/screens/choice_summary.py`
- Test: `tests/test_choice_screen.py`

**Interfaces:**
- Consumes: `CHOICE_GAMES`, `ChoiceSession`, `ChoiceProgressStore`, `level_suggestion_card`/`current_offer`/`decline`/`show_view` (`screens/level_suggestion.py`), `game_header`, `content_width`, `primary_button`.
- Produces: `build_choice_game_view(page, state, game: ChoiceGame) -> ft.View`, `build_choice_summary_view(page, state, game: ChoiceGame) -> ft.View`.

Screen behavior (copy is exact):
- Header: `game_header(f"{game.title} {icon}", accent, "חזרה לתפריט", exit, finish)`; then `שאלה {position} מתוך {total}` (+ ` · מתקדם` at advanced), then `game.prompt_line`.
- Prompt card: the word (size 34, bold) or the definition (size 22) in the theme's light box, width `content_width(page)`.
- Four option buttons stacked vertically, full `content_width`, min height 64, text size 22, wrapping. Wrong pick → that button turns pale red `#FFE3E3`, disabled, feedback `לא בדיוק, נסו שוב`. Correct → green `#D3F9D8`, feedback `מצוין! \U0001f389`, other buttons disabled, next button (`השאלה הבאה` / `לסיכום`) shown, progress saved.
- Level-suggestion card under the feedback (same pattern as `scramble_game.py`); unit word `שאלות` (card reads `פתרת 8 שאלות ברצף`). Accept → set level, new session, `show_view`.
- Summary: `ענית נכון בניסיון הראשון על {first_try_correct} מתוך {answered}`, best (hidden in public mode), suggestion card, `משחק חדש`, `חזרה לתפריט`.
- No background tasks (nothing to stop on leaving).

- [ ] **Step 1: Write the failing tests** (FakePage pattern from `tests/test_simon_game_screen.py`): `test_wrong_then_right_pick_flow` (feedback texts, button states, `next` visible only after correct), `test_progress_saved_after_each_answer`, `test_leaving_mid_game_keeps_progress`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run full `pytest -q` → PASS.
- [ ] **Step 5: Verify on a phone-sized browser:** run `uvicorn web:app --port 8550`, screenshot `/synonym`, `/opposite`, `/definition` at 360×640 and 360×740 with Playwright (scratchpad `shots.py`); expect no horizontal overflow, all 4 options visible, long definitions wrapping. Check the home screen shows the 3 new cards.
- [ ] **Step 6: Commit** — `git commit -m "Add game and summary screens for the choice games"`

### Task 7: Finish

- [ ] **Step 1:** `pytest -q` → all pass; `python scripts/find_word_candidates.py --check` → every new bank word confirmed.
- [ ] **Step 2:** Update README game list (add the three games) and the ויקימילון sources note (synonym/opposite banks); relaunch the desktop app for the user to try.
- [ ] **Step 3:** Ask the user to review; **push only after approval**: `git push origin main`.
