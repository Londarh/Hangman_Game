# Hangman

A web-based Hangman game for CSE 4095. It has three parts:

- a **game engine** in Python (`game.py`, `word_manager.py`) that knows nothing about the web,
- a **Flask server** (`server.py`) that exposes the engine through a JSON REST API,
- a **browser client** (`static/`: HTML, CSS, JavaScript) that talks to the server with `fetch()`.

The server owns all game logic and the hidden word. The browser only sends guesses and draws the state the server sends back; the word is revealed only after the game is won or lost.

Pick Easy, Medium or Hard, guess letters by clicking or typing, and you have 6 wrong guesses before the hangman is complete. Word lists live in `words/`.

Planning notes: [Assignment/TODO.md](Assignment/TODO.md) (phased plan) and [Assignment/Specification.md](Assignment/Specification.md) (original specification). The terminal client, bots, evaluation mode and leaderboard from the original specification are out of scope for this project.

## Install and run locally

Requires Python 3.10 or newer (developed and tested with 3.12).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements-dev.txt
python server.py
```

Open <http://127.0.0.1:5000>. Set the `PORT` environment variable to use a different port (for example `set PORT=8000` on Windows `cmd`, `$env:PORT=8000` in PowerShell, `PORT=8000 python server.py` on macOS/Linux).

`requirements.txt` holds what the app needs at runtime (Flask, Gunicorn). `requirements-dev.txt` adds `pytest` for the tests.

## Run the tests

```bash
python -m pytest
```

This runs the engine, word-list, API and static-file tests, plus an end-to-end test that starts `server.py` on a free port and plays games over real HTTP.

## REST API

All requests and responses are JSON. Every response, including errors, is JSON.

### Game state

Creating a game, reading it and guessing all return the same shape:

| Field | Meaning |
|---|---|
| `game_id` | Unique id (32 hex characters) |
| `pattern` | The word with unguessed letters as `_`, letters separated by spaces, e.g. `"_ e _ _ e"` |
| `guessed_letters` | Every letter guessed so far, in order |
| `incorrect_letters` | The guessed letters that are not in the word |
| `remaining_guesses` | Wrong guesses left (starts at 6) |
| `status` | `"playing"`, `"won"` or `"lost"` |
| `word` | The answer. **Only present once `status` is `won` or `lost`** |

### `POST /api/games` — create a game

Request body: `{"difficulty": "easy"}` (`easy`, `medium` or `hard`, case-insensitive; required).

```bash
curl -X POST http://127.0.0.1:5000/api/games -H "Content-Type: application/json" -d '{"difficulty":"easy"}'
```

`201 Created`:

```json
{
  "game_id": "d85722373a1b48f6b8d3607ed49dbcfc",
  "pattern": "_ _ _ _ _",
  "guessed_letters": [],
  "incorrect_letters": [],
  "remaining_guesses": 6,
  "status": "playing"
}
```

### `GET /api/games/{game_id}` — current state

```bash
curl http://127.0.0.1:5000/api/games/d85722373a1b48f6b8d3607ed49dbcfc
```

`200 OK` with the state object above.

### `POST /api/games/{game_id}/guess` — guess a letter

Request body: `{"letter": "e"}` — a single letter a–z, upper or lower case.

```bash
curl -X POST http://127.0.0.1:5000/api/games/d85722373a1b48f6b8d3607ed49dbcfc/guess -H "Content-Type: application/json" -d '{"letter":"t"}'
```

`200 OK`, while the game continues (a correct guess costs nothing, a wrong one costs a life):

```json
{
  "game_id": "d85722373a1b48f6b8d3607ed49dbcfc",
  "pattern": "_ t _ _ _",
  "guessed_letters": ["e", "t"],
  "incorrect_letters": ["e"],
  "remaining_guesses": 5,
  "status": "playing"
}
```

When the last letter is found or the last life is lost, the response has `"status": "won"` or `"lost"` and also includes the answer in `word`. A lost game looks like this (the pattern shows only what was guessed):

```json
{
  "game_id": "d85722373a1b48f6b8d3607ed49dbcfc",
  "pattern": "s t _ _ _",
  "guessed_letters": ["e", "t", "a", "o", "i", "n", "s", "r"],
  "incorrect_letters": ["e", "a", "o", "i", "n", "r"],
  "remaining_guesses": 0,
  "status": "lost",
  "word": "study"
}
```

In a win, `pattern` is the complete word and `remaining_guesses` is the number of lives left.

### Errors

Errors always look like `{"error": "message"}`. A rejected guess never changes the game.

| Status | When |
|---|---|
| `200 OK` | Game read, or guess accepted |
| `201 Created` | Game created |
| `400 Bad Request` | Body missing, not valid JSON, or not a JSON object; `difficulty` missing or not `easy`/`medium`/`hard`; `letter` missing, not a string, not a single a–z letter; letter already guessed |
| `404 Not Found` | Unknown `game_id`, or unknown URL |
| `405 Method Not Allowed` | Wrong HTTP method for the URL |
| `409 Conflict` | Guess on a game that is already won or lost |
| `500 Internal Server Error` | Unexpected server error (generic message, no internal details) |

```json
{"error": "letter 'e' was already guessed"}
```

## Project structure

```
Assignment/            Specification.md and TODO.md (planning documents)
words/                 easy.txt, medium.txt, hard.txt (one word per line)
game.py                HangmanGame: rules, win/loss, client-safe state (no Flask)
word_manager.py        Loads and validates word lists, picks a random word by difficulty
server.py              Flask app (module-level `app`) and the REST API
static/
  index.html           Page layout and the SVG hangman
  style.css            Styling, light/dark mode, phone layout
  app.js               fetch() calls to the API and drawing of the returned state
tests/                 pytest: engine, word lists, API, static files, end-to-end
requirements.txt       Runtime dependencies (installed on Render)
requirements-dev.txt   Adds pytest (not installed on Render)
render.yaml            Render Blueprint (free web service, Gunicorn, 1 worker)
pytest.ini             Test configuration
```

## Deploy on Render

The repository includes a Blueprint, [render.yaml](render.yaml), so Render can set everything up from it. It creates a free web service that installs `requirements.txt` and starts the app with:

```bash
gunicorn --bind 0.0.0.0:$PORT --workers 1 server:app
```

Render supplies `$PORT`. **Keep `--workers 1`**: games are stored in memory inside the server process, so a second worker would have its own empty set of games and a game created in one worker would be "not found" in the other. The Python version is pinned to 3.12.5 in `render.yaml` through the `PYTHON_VERSION` setting.

Steps:

1. Push this repository to GitHub (the repo contains no secrets; nothing needs to be configured as an environment variable).
2. Sign in at <https://dashboard.render.com> (you can sign in with GitHub) and allow Render to access the repository.
3. In the dashboard choose **New** → **Blueprint**, select the repository and branch, and apply it. Render reads `render.yaml` from the repository root and creates the `hangman` service. (Menu wording may differ slightly.)
4. Wait for the build and deploy to finish. The service's public `https://<name>.onrender.com` URL is shown at the top of its page.
5. Open the URL and play a full game. You can also check the API: `curl -X POST https://<name>.onrender.com/api/games -H "Content-Type: application/json" -d '{"difficulty":"easy"}'`.

Later pushes to the connected branch redeploy automatically (`autoDeployTrigger: commit`).

Prefer not to use the Blueprint? Create a **Web Service** manually from the repository with runtime **Python**, instance type **Free**, build command `pip install -r requirements.txt`, start command `gunicorn --bind 0.0.0.0:$PORT --workers 1 server:app`, and an environment variable `PYTHON_VERSION` = `3.12.5`.

Gunicorn does not run on native Windows, so use `python server.py` locally; Render runs Gunicorn on Linux.

## Manual browser checklist

Automated tests cannot see the page, so check these by hand in a browser (with the server running):

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
- [ ] DevTools > Network: a guess sends `POST /api/games/<id>/guess` with `{"letter": "e"}` and the JSON response contains the new state, with no `word` while the game is still playing.

## Known limitations

- **Games live in memory only.** They are lost whenever the server restarts. On Render's free plan the service also spins down after 15 minutes without traffic, which loses every game in progress. The page then tells the player to start a new game.
- **The first request after a spin-down is slow.** On the free plan, waking the service takes about a minute, and the browser shows a loading page until it is up.
- **Finished games are never cleaned up**, so memory grows slowly for as long as the server keeps running.
- **Single process only.** The server must run with one worker (see above); it cannot be scaled out without moving game storage out of memory.
- There are no accounts, no persistence across restarts and no limit on how many games a client can create.
