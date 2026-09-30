import random

from simon.hebrew_letters import to_base_form
from simon.letter_puzzle import GuessResult, LetterPuzzle, scramble_letters


def _puzzle(answer="שלום", seed=0):
    return LetterPuzzle(answer, scramble_letters(answer, random.Random(seed)))


def _tap_answer(puzzle):
    """Taps tiles in the order that spells the answer."""
    used = []
    for letter in to_base_form(puzzle.answer):
        index = next(i for i, t in enumerate(puzzle.tiles) if t == letter and i not in used)
        used.append(index)
        puzzle.tap_tile(index)


def test_scramble_is_a_permutation_different_from_the_word():
    rng = random.Random(0)
    for word in ["שלום", "סוס", "מלפפון"]:
        for _ in range(20):
            letters = scramble_letters(word, rng)
            assert sorted(letters) == sorted(to_base_form(word))
            assert "".join(letters) != to_base_form(word)


def test_scramble_uses_non_final_letter_forms():
    letters = scramble_letters("שלום", random.Random(0))
    assert "ם" not in letters
    assert "מ" in letters


def test_correct_spelling_solves_the_word():
    puzzle = _puzzle()
    _tap_answer(puzzle)
    assert puzzle.check_attempt() == GuessResult.CORRECT
    assert puzzle.solved and puzzle.done
    assert not puzzle.revealed


def test_partial_attempt_is_incomplete():
    puzzle = _puzzle()
    puzzle.tap_tile(0)
    assert puzzle.check_attempt() == GuessResult.INCOMPLETE
    assert not puzzle.done


def test_wrong_full_attempt_is_wrong_and_left_intact():
    puzzle = _puzzle()
    # the scramble itself is guaranteed not to be the answer
    for i in range(len(puzzle.tiles)):
        puzzle.tap_tile(i)
    assert puzzle.check_attempt() == GuessResult.WRONG
    assert puzzle.current_attempt == list(range(len(puzzle.tiles)))
    assert not puzzle.solved


def test_tiles_in_another_words_order_can_be_rearranged():
    # the change-a-word game starts from one word's letters in order
    puzzle = LetterPuzzle("אפור", list("רופא"))
    for i in [3, 2, 1, 0]:
        puzzle.tap_tile(i)
    assert puzzle.check_attempt() == GuessResult.CORRECT


def test_tapping_same_tile_twice_is_ignored():
    puzzle = _puzzle()
    puzzle.tap_tile(0)
    puzzle.tap_tile(0)
    assert puzzle.current_attempt == [0]


def test_undo_and_clear():
    puzzle = _puzzle()
    puzzle.tap_tile(0)
    puzzle.tap_tile(1)
    puzzle.undo_last()
    assert puzzle.current_attempt == [0]
    puzzle.clear_attempt()
    assert puzzle.current_attempt == []


def test_slot_letters_pad_with_empty_and_apply_final_form_when_full():
    puzzle = _puzzle("שלום")
    assert puzzle.slot_letters() == ["", "", "", ""]
    _tap_answer(puzzle)
    assert puzzle.slot_letters() == list("שלום")


def test_hint_places_next_correct_letter():
    puzzle = _puzzle()
    assert puzzle.hint_next_letter()
    assert puzzle.slot_letters()[0] == to_base_form(puzzle.answer)[0]
    assert puzzle.hints_used == 1


def test_hint_drops_wrong_letters_after_correct_prefix():
    puzzle = _puzzle("שלום")
    target = to_base_form(puzzle.answer)
    wrong = next(i for i, t in enumerate(puzzle.tiles) if t != target[0])
    puzzle.tap_tile(wrong)
    puzzle.hint_next_letter()
    assert [puzzle.tiles[i] for i in puzzle.current_attempt] == [target[0]]


def test_hints_alone_can_complete_the_word():
    puzzle = _puzzle("מלפפון")
    while puzzle.hint_next_letter():
        pass
    assert puzzle.check_attempt() == GuessResult.CORRECT
    assert puzzle.slot_letters() == list("מלפפון")


def test_reveal_marks_done_without_solving():
    puzzle = _puzzle()
    puzzle.reveal()
    assert puzzle.done and puzzle.revealed
    assert not puzzle.solved
    assert "".join(puzzle.slot_letters()) == puzzle.answer


def test_taps_ignored_once_word_is_done():
    puzzle = _puzzle()
    puzzle.reveal()
    before = list(puzzle.current_attempt)
    puzzle.undo_last()
    puzzle.clear_attempt()
    puzzle.tap_tile(0)
    assert puzzle.current_attempt == before
    assert not puzzle.hint_next_letter()
