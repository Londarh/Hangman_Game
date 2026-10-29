import ast
import pathlib

import pytest

from game import GameOverError, HangmanGame, InvalidGuessError


def play_to_win(game, word):
    for c in sorted(set(word)):
        game.guess(c)


def play_to_loss(game, wrong="zqxjkv"):
    for c in wrong:
        game.guess(c)


def test_initial_state():
    state = HangmanGame("eagle").to_state()
    assert state == {
        "pattern": "_ _ _ _ _",
        "guessed_letters": [],
        "incorrect_letters": [],
        "remaining_guesses": 6,
        "status": "playing",
    }


def test_correct_guess_reveals_letters_and_costs_nothing():
    game = HangmanGame("eagle")
    state = game.guess("e")
    assert state["pattern"] == "e _ _ _ e"
    assert state["guessed_letters"] == ["e"]
    assert state["incorrect_letters"] == []
    assert state["remaining_guesses"] == 6
    assert state["status"] == "playing"


def test_incorrect_guess_costs_a_life():
    game = HangmanGame("eagle")
    state = game.guess("z")
    assert state["pattern"] == "_ _ _ _ _"
    assert state["incorrect_letters"] == ["z"]
    assert state["remaining_guesses"] == 5


def test_uppercase_and_lowercase_guesses_both_work():
    game = HangmanGame("eagle")
    assert game.guess("E")["pattern"] == "e _ _ _ e"
    assert game.guess("Z")["incorrect_letters"] == ["z"]
    assert game.guess("a")["guessed_letters"] == ["e", "z", "a"]


def test_uppercase_word_is_normalized():
    game = HangmanGame("EAGLE")
    assert game.guess("e")["pattern"] == "e _ _ _ e"
    for c in "agl":
        game.guess(c)
    assert game.to_state()["word"] == "eagle"


def test_guess_same_letter_different_case_is_duplicate():
    game = HangmanGame("eagle")
    game.guess("e")
    with pytest.raises(InvalidGuessError):
        game.guess("E")


def test_win():
    game = HangmanGame("eagle")
    play_to_win(game, "eagle")
    state = game.to_state()
    assert state["status"] == "won"
    assert state["pattern"] == "e a g l e"
    assert state["word"] == "eagle"
    assert state["remaining_guesses"] == 6


def test_loss_after_six_wrong_guesses():
    game = HangmanGame("eagle")
    play_to_loss(game)
    state = game.to_state()
    assert state["status"] == "lost"
    assert state["remaining_guesses"] == 0
    assert state["incorrect_letters"] == list("zqxjkv")
    assert state["word"] == "eagle"


def test_five_wrong_guesses_still_playing():
    game = HangmanGame("eagle")
    play_to_loss(game, "zqxjk")
    assert game.status == "playing"
    assert game.remaining_guesses == 1


def test_win_on_last_life():
    game = HangmanGame("eagle")
    play_to_loss(game, "zqxjk")
    play_to_win(game, "eagle")
    assert game.status == "won"
    assert game.remaining_guesses == 1


def test_word_hidden_while_playing():
    game = HangmanGame("eagle")
    game.guess("e")
    game.guess("z")
    state = game.to_state()
    assert "word" not in state
    assert "eagle" not in repr(state)


@pytest.mark.parametrize("bad", ["", "ab", "1", " ", "!", "é", "ß", None, 5, ["a"]])
def test_invalid_guess_raises_and_changes_nothing(bad):
    game = HangmanGame("eagle")
    game.guess("e")
    before = game.to_state()
    with pytest.raises(InvalidGuessError):
        game.guess(bad)
    assert game.to_state() == before


def test_duplicate_guess_raises_and_changes_nothing():
    game = HangmanGame("eagle")
    game.guess("e")
    game.guess("z")
    before = game.to_state()
    for dup in ("e", "z"):
        with pytest.raises(InvalidGuessError, match="already guessed"):
            game.guess(dup)
    assert game.to_state() == before


@pytest.mark.parametrize("outcome", ["won", "lost"])
def test_guess_after_game_over_raises_and_changes_nothing(outcome):
    game = HangmanGame("eagle")
    if outcome == "won":
        play_to_win(game, "eagle")
    else:
        play_to_loss(game)
    before = game.to_state()
    with pytest.raises(GameOverError):
        game.guess("b")
    with pytest.raises(GameOverError):
        game.guess("e")
    assert game.to_state() == before
    assert game.status == outcome


def test_game_over_error_is_an_invalid_guess_error():
    assert issubclass(GameOverError, InvalidGuessError)


@pytest.mark.parametrize("bad", ["", "  ", "two words", "abc1", "café", None, 123])
def test_invalid_word_rejected(bad):
    with pytest.raises(ValueError):
        HangmanGame(bad)


def test_max_incorrect_is_configurable():
    game = HangmanGame("eagle", max_incorrect=2)
    game.guess("z")
    game.guess("q")
    assert game.status == "lost"


def test_games_are_independent():
    a, b = HangmanGame("eagle"), HangmanGame("eagle")
    a.guess("e")
    assert b.to_state()["guessed_letters"] == []


def test_state_is_a_copy():
    game = HangmanGame("eagle")
    game.guess("z")
    state = game.to_state()
    state["incorrect_letters"].append("hack")
    state["guessed_letters"].clear()
    assert game.to_state()["incorrect_letters"] == ["z"]
    assert game.to_state()["guessed_letters"] == ["z"]


def test_engine_has_no_web_imports():
    source = pathlib.Path(__file__).resolve().parent.parent / "game.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert not imported & {"flask", "werkzeug", "jinja2", "gunicorn", "requests", "http", "urllib"}
