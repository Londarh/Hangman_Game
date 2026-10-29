"""Word lists and random word selection. Pure Python: no web framework dependencies."""

import random
from pathlib import Path

DIFFICULTIES = ("easy", "medium", "hard")
DEFAULT_WORDS_DIR = Path(__file__).resolve().parent / "words"


class InvalidDifficultyError(ValueError):
    """Raised for a difficulty other than easy, medium or hard."""


class InvalidWordError(ValueError):
    """Raised when a word list contains an entry that is not purely letters."""


def normalize_difficulty(difficulty):
    if isinstance(difficulty, str):
        name = difficulty.strip().lower()
        if name in DIFFICULTIES:
            return name
    raise InvalidDifficultyError(
        f"invalid difficulty {difficulty!r}; expected one of: {', '.join(DIFFICULTIES)}"
    )


def load_words(path):
    """Read one word list: stripped, lowercased, blanks skipped, duplicates dropped.

    Order of first appearance is kept. Raises InvalidWordError (naming the file and
    line) if an entry contains anything other than the letters a-z.
    """
    path = Path(path)
    words = []
    seen = set()
    with path.open(encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            word = line.strip().lower()
            if not word:
                continue
            if not (word.isascii() and word.isalpha()):
                raise InvalidWordError(
                    f"{path.name} line {line_number}: {word!r} contains non-letter characters"
                )
            if word not in seen:
                seen.add(word)
                words.append(word)
    return words


class WordManager:
    def __init__(self, words_dir=DEFAULT_WORDS_DIR):
        self.words_dir = Path(words_dir)
        self._words = {d: load_words(self.words_dir / f"{d}.txt") for d in DIFFICULTIES}

    def words(self, difficulty):
        """Return a copy of the word list for a difficulty."""
        return list(self._words[normalize_difficulty(difficulty)])

    def random_word(self, difficulty, rng=random):
        return rng.choice(self._words[normalize_difficulty(difficulty)])
