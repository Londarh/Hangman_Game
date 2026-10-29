"""Hangman game engine. Pure Python: no web framework or UI dependencies."""

MAX_INCORRECT = 6

PLAYING = "playing"
WON = "won"
LOST = "lost"


class InvalidGuessError(ValueError):
    """Raised when a guess is rejected; the game state is left unchanged."""


class GameOverError(InvalidGuessError):
    """Raised when a guess is made after the game has ended."""


class HangmanGame:
    def __init__(self, word, max_incorrect=MAX_INCORRECT):
        word = word.strip().lower() if isinstance(word, str) else ""
        if not word or not (word.isascii() and word.isalpha()):
            raise ValueError("word must be a non-empty string of letters a-z")
        if max_incorrect < 1:
            raise ValueError("max_incorrect must be at least 1")
        self._word = word
        self.max_incorrect = max_incorrect
        self.guessed_letters = []
        self.incorrect_letters = []

    @property
    def remaining_guesses(self):
        return self.max_incorrect - len(self.incorrect_letters)

    @property
    def status(self):
        if all(c in self.guessed_letters for c in self._word):
            return WON
        if self.remaining_guesses <= 0:
            return LOST
        return PLAYING

    @property
    def pattern(self):
        return " ".join(c if c in self.guessed_letters else "_" for c in self._word)

    def guess(self, letter):
        """Apply a guess and return the new state.

        Raises GameOverError if the game has ended, or InvalidGuessError if the
        guess is not a single letter or was already guessed. The game is not
        modified when an error is raised.
        """
        if self.status != PLAYING:
            raise GameOverError("the game is already over")
        if not isinstance(letter, str) or len(letter) != 1 or not (letter.isascii() and letter.isalpha()):
            raise InvalidGuessError("a guess must be a single letter a-z")
        letter = letter.lower()
        if letter in self.guessed_letters:
            raise InvalidGuessError(f"letter '{letter}' was already guessed")

        self.guessed_letters.append(letter)
        if letter not in self._word:
            self.incorrect_letters.append(letter)
        return self.to_state()

    def to_state(self):
        """Client-safe state; includes `word` only once the game has ended."""
        status = self.status
        state = {
            "pattern": self.pattern,
            "guessed_letters": list(self.guessed_letters),
            "incorrect_letters": list(self.incorrect_letters),
            "remaining_guesses": self.remaining_guesses,
            "status": status,
        }
        if status != PLAYING:
            state["word"] = self._word
        return state
