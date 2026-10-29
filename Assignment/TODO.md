# TODO — Web Hangman (Game Engine, Flask API, Browser Client, Deploy)

Reduced-scope plan for the CSE 4095 assignment. Requirements: `hangman_assignment.md`. Original spec: `Specification.md` (the old TODO called it `Hangman_Project_Specification.md`).

## Rules

- One phase at a time. Each phase ends in a reviewable, committable state; the app stays runnable.
- Tests are written in the same phase as the code, not at the end.
- The game engine (`game.py`) must not import Flask or touch the browser.
- The server is authoritative. The hidden word is never sent while `status` is `playing`, and the browser never holds it.
- No secrets in the repo.
- Update this file only after a phase is verified. After each phase: review, commit, push.

## Target layout (repo root = `hangsman_game/`)

```
Assignment/        Specification.md, TODO.md, assignment text
words/             easy.txt, medium.txt, hard.txt
game.py            HangmanGame (no Flask)
word_manager.py    load lists, random word by difficulty
server.py          Flask app, module-level `app`
static/            index.html, style.css, app.js
tests/
requirements.txt, render.yaml, README.md, .gitignore
```

## API decisions to lock in (spec leaves these open)

- Status codes: 201 create, 200 get/guess, 400 invalid input or duplicate guess, 404 unknown game id, 409 guess on a finished game.
- Duplicate guess: reject (400), state unchanged.
- Guess on a finished game: reject (409), state unchanged.
- Pattern format: letters separated by spaces, e.g. `"_ e _ _ e"`.
- Answer field: `word`, present only when status is `won` or `lost`.
- Same state shape from create, get and guess: `game_id`, `pattern`, `guessed_letters`, `incorrect_letters`, `remaining_guesses`, `status`, plus `word` after the game ends.
- Six incorrect guesses allowed; correct guesses cost nothing.

---

## Phase 1 — Repo and skeleton

- [x] Git repo, Python `.gitignore`, origin set to the GitHub repo.
- [x] First commit: `Specification.md`, this TODO, `words/*.txt`.
- [x] `requirements.txt` (`flask`, `gunicorn`), `requirements-dev.txt` (adds `pytest`), `pytest.ini`, `tests/`, stub `README.md`.

Done when: repo is on GitHub and `pip install -r requirements.txt` works in a fresh venv.

## Phase 2 — Game engine (`game.py`)

- [x] `HangmanGame(word, max_incorrect=6)`; lowercases the word.
- [x] `guess(letter)`: validates a single a–z letter; rejects duplicates and guesses after the game ends (custom exception).
- [x] Tracks guessed and incorrect letters and remaining guesses.
- [x] Masked pattern, win/loss detection, status `playing` / `won` / `lost`.
- [x] `to_state()` returns the client-safe dict; includes `word` only when finished.
- [x] Unit tests (`unittest` or `pytest`): correct/incorrect, repeated, invalid, win, loss, no guess after end, no word leak while playing.

Done when: engine tests pass with no server involved.

## Phase 3 — Word management (`word_manager.py`)

- [x] Load `words/easy|medium|hard.txt` (path relative to the file, not the CWD).
- [x] Lowercase, skip blanks, drop duplicates, reject non-alphabetic entries.
- [x] `random_word(difficulty)`; unknown difficulty raises a clear error.
- [x] Tests: all three levels load, selection is from the right list, invalid difficulty rejected.

Done when: each difficulty returns valid words and bad input is rejected cleanly.

## Phase 4 — Flask API (`server.py`)

- [x] In-memory game store; unique ids (`uuid4` or `secrets`).
- [x] `POST /api/games` (body `{"difficulty": ...}`; decide the default if omitted).
- [x] `GET /api/games/<id>`.
- [x] `POST /api/games/<id>/guess` (body `{"letter": ...}`).
- [x] JSON in and out; consistent error body such as `{"error": "..."}`; malformed or non-JSON bodies return 400, not 500.
- [x] Module-level `app`; debug mode off by default.
- [x] API tests with Flask's test client: all difficulties, correct/incorrect/duplicate/invalid guesses, win, loss, guess after end, unknown id, bad difficulty, bad JSON, separate games stay independent, no `word` while playing.

Done when: a full game can be played with `curl` and the tests pass.

## Phase 5 — Browser client (`static/`)

- [x] Serve `index.html` at `/`.
- [x] Difficulty selector and New Game button (no page reload).
- [x] Masked word, guessed letters, incorrect letters, remaining guesses.
- [x] On-screen A–Z buttons plus physical keyboard input; guessed letters disabled.
- [x] `fetch()` to the API only; no game logic and no word in JS.
- [x] SVG hangman that gains a part per incorrect guess.
- [x] Win/loss message that shows the revealed word (from the API response).
- [x] Show API errors instead of failing silently; usable at phone width.
- [x] Test that `/` and static files are served; manual play-through in the browser.

Done when: a complete game can be played in the browser and a second game starts without reloading.

## Phase 6 — Testing and hardening

- [x] Run the full suite; fill any gaps against the assignment's test list (3 difficulties, correct/incorrect, repeated/invalid, win/loss, new game after finishing, invalid requests, no word leak, UI updates after each guess).
- [x] One end-to-end test that plays a full game through the HTTP API.
- [x] Manual checklist in the README for the browser behaviour.
- [x] Chrome DevTools check: inspect one guess request and JSON response (done by you in Chrome while walking through the README checklist).
- [x] Fix anything found; list known limitations.

Done when: all tests pass (also verified in a fresh venv) and the manual checklist has been walked through once (done).

## Phase 7 — Deployment prep and README

- [x] Verify locally with Gunicorn (needs WSL/Linux or Render's own build; Gunicorn does not run on native Windows): `gunicorn --bind 0.0.0.0:$PORT --workers 1 server:app`. On Windows, `flask run` or `python server.py` for local testing.
- [x] `render.yaml` (or documented dashboard settings): Python web service, build `pip install -r requirements.txt`, start command above, free plan.
- [x] `--workers 1` is required because games live in memory.
- [x] README: what it is, run locally, run tests, API reference with examples, deploy notes, known limitations (games are lost on restart or when the free instance sleeps).

Done when: a fresh clone follows the README and runs locally. (Gunicorn verified under WSL Ubuntu: one master plus one worker, `$PORT` respected.)

## Phase 8 — Deploy on Render

- [x] Push to GitHub, connect the repo in Render, create the web service (manual step).
- [x] Open the public HTTPS URL and play a full game in the browser.
- [x] Hit the API on the live URL (create, get, guess) with `curl` or DevTools.
- [x] Put the live URL in the README.

Done when: the deployed app works end to end, independent of the local machine. Live: https://hangman-6ckj.onrender.com/

## Phase 9 — Submission materials (not code)

- [ ] Repo contains: engine, server, frontend, word lists, spec, updated TODO, requirements/deploy config, tests, README.
- [ ] Development report (PDF, 1–2 pages) with 2–3 representative prompts.
- [ ] 2–3 minute screen recording (deployed page, win or loss, new game, one request/response in DevTools).
- [ ] Submit repo URL, live URL, report and recording on HuskyCT.

---

## OUT OF SCOPE for this assignment (kept for reference, not to be implemented)

Original phases that the assignment excludes:

- ~~Original Phase 4 — Human Terminal Client~~ (`terminal_client.py`) — **OUT OF SCOPE**
- ~~Original Phase 6 — Reference Automated Clients~~ (random and frequency bots) — **OUT OF SCOPE**
- ~~Original Phase 7 — Dictionary-Based Bot~~ — **OUT OF SCOPE**
- ~~Original Phase 8 — Evaluation Mode~~ (`/api/evaluation/*`) — **OUT OF SCOPE**
- ~~Original Phase 9 — Scoring System~~ — **OUT OF SCOPE**
- ~~Original Phase 10 — Leaderboard~~ — **OUT OF SCOPE**
- ~~Original Phase 11 — Evaluation Integrity and Anti-Cheating~~ (rate limits, idle timeouts) — **OUT OF SCOPE** (the "no word leak while playing" rule is kept in Phases 2 and 4)
- ~~Original Phase 12 — Logging and Replay~~ (`/log`, `/replay`, `replay.py`) — **OUT OF SCOPE** (not required by the assignment; optional extra only)
- ~~Optional future phases~~ (database, accounts, tournaments, entropy bots, multiplayer) — **OUT OF SCOPE**

Original phases 1, 2, 3, 5, 13, 14 are folded into Phases 2, 3, 4, 5, 6, 7 above.
