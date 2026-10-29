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

## Run the tests

```bash
python -m pytest
```

Running the app, the API reference and deployment notes will be added in later phases.
