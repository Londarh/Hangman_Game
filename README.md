# Hangman

A web-based Hangman game: a Python game engine, a Flask REST API, and a browser client (HTML/CSS/JavaScript). Built for CSE 4095.

The server holds all game logic and the hidden word; the browser only talks to the REST API.

## Status

Work in progress. See [Assignment/TODO.md](Assignment/TODO.md) for the phased plan and [Assignment/Specification.md](Assignment/Specification.md) for the original specification. Terminal client, bots, evaluation and leaderboard are out of scope.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
```

## Run locally

```bash
python server.py
```

Then open <http://127.0.0.1:5000>. Set the `PORT` environment variable to use another port.

## Run the tests

```bash
python -m pytest
```

This runs the engine, word-list, API and static-file tests, plus an end-to-end test that starts `server.py` on a free port and plays games over real HTTP.

## Manual browser checklist

Automated tests cannot see the page, so check these by hand in a browser (with `python server.py` running):

- [ ] The page loads and a new game starts automatically: blank pattern (`_ _ _ ...`), 6 wrong guesses left, empty gallows, all 26 keys enabled.
- [ ] Clicking a letter updates the pattern, guessed letters, wrong letters and remaining count straight away, without reloading the page.
- [ ] Correct guesses fill in every matching position; the key turns green and becomes disabled.
- [ ] Each wrong guess adds exactly one body part (head, body, left arm, right arm, left leg, right leg) and turns the key red; the figure is complete at 6.
- [ ] Typing letters on the physical keyboard works the same as clicking, including typing several letters quickly.
- [ ] Typing an already-guessed letter does nothing, and double-clicking a key sends only one guess (see the Network tab).
- [ ] Winning shows a green message with the word; losing shows a red message with the word; after either, all keys are disabled.
- [ ] New Game works at any time (mid-game and after a win/loss) and resets the figure, keys and messages; changing the difficulty and pressing New Game gives a longer or shorter word.
- [ ] Phone width (browser dev tools, ~375px wide): no sideways scrolling, keys are easy to tap, the drawing and word stay readable.
- [ ] With the server stopped, pressing New Game or a letter shows an error message instead of failing silently.
- [ ] DevTools > Network: a guess sends `POST /api/games/<id>/guess` with `{"letter": "e"}` and the JSON response contains the new state, with no `word` while the game is still playing. (Needed for the demo recording.)

## Known limitations

- Games are stored in memory only. They are lost when the server restarts or, on Render's free plan, when the idle service sleeps. The page then tells the player to start a new game.
- Finished games are never cleaned up, so memory grows slowly for as long as the server runs.
- The server must run as a single process (`--workers 1`), because each worker would have its own set of games.

Running on Render, the API reference and deployment notes will be added in later phases.
