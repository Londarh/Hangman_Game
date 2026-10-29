"""End-to-end test: start the real server process and play over actual HTTP."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from word_manager import WordManager

ROOT = Path(__file__).resolve().parent.parent
ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "server.py"], cwd=ROOT,
        env={**os.environ, "PORT": str(port)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 15
        while True:
            try:
                urllib.request.urlopen(url + "/", timeout=1).close()
                break
            except OSError:
                if proc.poll() is not None or time.time() > deadline:
                    pytest.fail("server did not start")
                time.sleep(0.1)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, resp.headers.get_content_type(), resp.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get_content_type(), err.read().decode()


def play_to_the_end(base_url, difficulty):
    status, ctype, text = http("POST", f"{base_url}/api/games", {"difficulty": difficulty})
    assert (status, ctype) == (201, "application/json")
    state = json.loads(text)
    game_id, states_while_playing = state["game_id"], [state]

    # Guessing every distinct letter always ends the game, as a win or a loss.
    for letter in ALPHABET:
        if state["status"] != "playing":
            break
        status, _, text = http("POST", f"{base_url}/api/games/{game_id}/guess", {"letter": letter})
        assert status == 200
        state = json.loads(text)
        if state["status"] == "playing":
            states_while_playing.append(state)
    return game_id, state, states_while_playing


def test_real_server_serves_the_page_and_static_files(base_url):
    status, ctype, html = http("GET", base_url + "/")
    assert (status, ctype) == (200, "text/html") and "Hangman" in html
    assert http("GET", base_url + "/static/app.js")[:2] == (200, "text/javascript")
    assert http("GET", base_url + "/static/style.css")[:2] == (200, "text/css")


def test_full_game_over_real_http_for_every_difficulty(base_url):
    manager = WordManager()
    for difficulty in ("easy", "medium", "hard"):
        game_id, final, playing_states = play_to_the_end(base_url, difficulty)

        assert final["status"] in ("won", "lost")
        word = final["word"]
        assert word in manager.words(difficulty)
        for s in playing_states:  # no answer field, and the pattern never spells out the word
            assert "word" not in s and s["pattern"].replace(" ", "") != word
        if final["status"] == "won":
            assert final["pattern"] == " ".join(word)
        else:
            assert final["remaining_guesses"] == 0 and len(final["incorrect_letters"]) == 6

        # the finished game stays readable, and further guesses are refused
        status, _, text = http("GET", f"{base_url}/api/games/{game_id}")
        assert status == 200 and json.loads(text) == final
        status, ctype, text = http("POST", f"{base_url}/api/games/{game_id}/guess", {"letter": "a"})
        assert (status, ctype) == (409, "application/json") and "error" in json.loads(text)


def test_new_game_after_finishing_over_real_http(base_url):
    first_id, first_final, _ = play_to_the_end(base_url, "easy")
    status, _, text = http("POST", f"{base_url}/api/games", {"difficulty": "medium"})
    second = json.loads(text)
    assert status == 201 and second["game_id"] != first_id
    assert second["status"] == "playing" and "word" not in second
    assert json.loads(http("GET", f"{base_url}/api/games/{first_id}")[2]) == first_final


def test_invalid_requests_over_real_http(base_url):
    for method, path, body, expected in [
        ("POST", "/api/games", {"difficulty": "extreme"}, 400),
        ("POST", "/api/games", {}, 400),
        ("GET", "/api/games/unknown", None, 404),
        ("POST", "/api/games/unknown/guess", {"letter": "a"}, 404),
        ("GET", "/nope", None, 404),
        ("DELETE", "/api/games", None, 405),
    ]:
        status, ctype, text = http(method, base_url + path, body)
        assert (status, ctype) == (expected, "application/json"), (method, path)
        assert "error" in json.loads(text)
