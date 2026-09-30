from simon.letter_puzzle import GuessResult
from simon.typed_puzzle import TypedPuzzle


def _type(puzzle, word):
    for letter in word:
        puzzle.type_letter(letter)


def test_typing_the_word_solves_it():
    puzzle = TypedPuzzle("אפור")
    _type(puzzle, "אפור")
    assert puzzle.check_attempt() == GuessResult.CORRECT
    assert puzzle.solved and puzzle.done


def test_final_and_regular_letter_forms_are_interchangeable():
    for typed in ["שלום", "שלומ"]:
        puzzle = TypedPuzzle("שלום")
        _type(puzzle, typed)
        assert puzzle.check_attempt() == GuessResult.CORRECT
        assert puzzle.slot_letters() == list("שלום")


def test_wrong_word_is_wrong_and_left_for_editing():
    puzzle = TypedPuzzle("אפור")
    _type(puzzle, "רופא")
    assert puzzle.check_attempt() == GuessResult.WRONG
    assert not puzzle.done
    puzzle.backspace()
    assert puzzle.typed == list("רופ")


def test_partial_is_incomplete_and_typing_stops_at_length():
    puzzle = TypedPuzzle("אפור")
    _type(puzzle, "אפ")
    assert puzzle.check_attempt() == GuessResult.INCOMPLETE
    assert puzzle.slot_letters() == ["א", "פ", "", ""]
    _type(puzzle, "וריי")
    assert len(puzzle.typed) == 4


def test_hint_keeps_correct_prefix_and_types_next_letter():
    puzzle = TypedPuzzle("אפור")
    _type(puzzle, "אק")
    assert puzzle.hint_next_letter()
    assert puzzle.typed == list("אפ")
    assert puzzle.hints_used == 1


def test_hints_alone_complete_the_word():
    puzzle = TypedPuzzle("מלפפון")
    while puzzle.hint_next_letter():
        pass
    assert puzzle.check_attempt() == GuessResult.CORRECT


def test_reveal_fills_answer_without_solving():
    puzzle = TypedPuzzle("שלום")
    puzzle.reveal()
    assert puzzle.revealed and puzzle.done and not puzzle.solved
    assert "".join(puzzle.slot_letters()) == "שלום"


def test_no_editing_once_done():
    puzzle = TypedPuzzle("אפור")
    puzzle.reveal()
    puzzle.backspace()
    puzzle.clear()
    puzzle.type_letter("ק")
    assert "".join(puzzle.typed) == "אפור"
