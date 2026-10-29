import ast
import random
from pathlib import Path

import pytest

import word_manager
from word_manager import (
    DIFFICULTIES,
    InvalidDifficultyError,
    InvalidWordError,
    WordManager,
    load_words,
    normalize_difficulty,
)


@pytest.fixture
def words_dir(tmp_path):
    (tmp_path / "easy.txt").write_text("cat\ndog\nsun\n", encoding="utf-8")
    (tmp_path / "medium.txt").write_text("planet\nbridge\n", encoding="utf-8")
    (tmp_path / "hard.txt").write_text("architecture\n", encoding="utf-8")
    return tmp_path


def write(tmp_path, text, name="words.txt"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_load_strips_lowercases_skips_blanks_and_dedupes(tmp_path):
    path = write(tmp_path, "  Cat \n\n\t\nDOG\ncat\r\nDog\n   \nsun")
    assert load_words(path) == ["cat", "dog", "sun"]


def test_load_handles_crlf_and_bom(tmp_path):
    path = write(tmp_path, "﻿cat\r\ndog\r\n")
    assert load_words(path) == ["cat", "dog"]


def test_load_empty_file_gives_empty_list(tmp_path):
    assert load_words(write(tmp_path, "\n  \n")) == []


@pytest.mark.parametrize("bad", ["ca7", "two words", "it's", "well-known", "café", "12", "a.b"])
def test_load_rejects_non_letters_with_clear_message(tmp_path, bad):
    path = write(tmp_path, f"cat\n{bad}\ndog\n", name="easy.txt")
    with pytest.raises(InvalidWordError) as exc:
        load_words(path)
    message = str(exc.value)
    assert "easy.txt" in message and "line 2" in message and repr(bad.lower()) in message


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_words(tmp_path / "nope.txt")


@pytest.mark.parametrize("name", ["easy", "Easy", "EASY", " medium ", "Hard"])
def test_difficulty_is_case_insensitive(name):
    assert normalize_difficulty(name) in DIFFICULTIES
    assert normalize_difficulty(name) == name.strip().lower()


@pytest.mark.parametrize("bad", ["", "extreme", "easy medium", None, 1, ["easy"]])
def test_invalid_difficulty_rejected_with_clear_message(bad):
    with pytest.raises(InvalidDifficultyError) as exc:
        normalize_difficulty(bad)
    assert "easy, medium, hard" in str(exc.value)


def test_random_word_comes_from_the_right_list(words_dir):
    manager = WordManager(words_dir)
    for _ in range(30):
        assert manager.random_word("easy") in {"cat", "dog", "sun"}
        assert manager.random_word("medium") in {"planet", "bridge"}
        assert manager.random_word("hard") == "architecture"


def test_random_word_accepts_mixed_case_difficulty(words_dir):
    assert WordManager(words_dir).random_word("Hard") == "architecture"


def test_random_word_invalid_difficulty(words_dir):
    manager = WordManager(words_dir)
    with pytest.raises(InvalidDifficultyError):
        manager.random_word("impossible")
    with pytest.raises(InvalidDifficultyError):
        manager.words("impossible")


def test_random_word_is_deterministic_with_seeded_rng(words_dir):
    manager = WordManager(words_dir)
    first = [manager.random_word("easy", rng=random.Random(7)) for _ in range(3)]
    assert first == [first[0]] * 3


def test_random_word_actually_varies(words_dir):
    manager = WordManager(words_dir)
    assert len({manager.random_word("easy") for _ in range(200)}) == 3


def test_words_returns_a_copy(words_dir):
    manager = WordManager(words_dir)
    manager.words("easy").clear()
    assert manager.words("easy") == ["cat", "dog", "sun"]


def test_bad_word_file_fails_at_construction(words_dir):
    (words_dir / "hard.txt").write_text("fine\nnot fine\n", encoding="utf-8")
    with pytest.raises(InvalidWordError, match="hard.txt"):
        WordManager(words_dir)


def test_missing_list_fails_at_construction(words_dir):
    (words_dir / "medium.txt").unlink()
    with pytest.raises(FileNotFoundError):
        WordManager(words_dir)


def test_default_words_dir_is_next_to_the_code_not_the_cwd(tmp_path, monkeypatch):
    expected = Path(word_manager.__file__).resolve().parent / "words"
    assert word_manager.DEFAULT_WORDS_DIR == expected
    monkeypatch.chdir(tmp_path)
    assert WordManager().random_word("easy")


def test_real_word_lists_load_and_are_not_empty():
    manager = WordManager()
    for difficulty in DIFFICULTIES:
        words = manager.words(difficulty)
        assert words, f"{difficulty}.txt is empty"
        assert all(w.isascii() and w.isalpha() and w == w.lower() for w in words)
        assert len(words) == len(set(words))
        assert manager.random_word(difficulty) in words


def test_word_manager_has_no_web_imports():
    source = Path(__file__).resolve().parent.parent / "word_manager.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert not imported & {"flask", "werkzeug", "jinja2", "gunicorn", "requests", "http", "urllib"}
