import re
from pathlib import Path

import pytest

import server
from word_manager import DIFFICULTIES, WordManager

STATIC = Path(server.__file__).resolve().parent / "static"


@pytest.fixture
def client():
    return server.create_app().test_client()


def test_root_serves_the_game_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"
    html = resp.get_data(as_text=True)
    assert "<title>Hangman</title>" in html
    for element_id in ("difficulty", "new-game", "pattern", "remaining", "guessed", "wrong",
                       "message", "error", "keyboard", "hangman"):
        assert f'id="{element_id}"' in html
    for value in DIFFICULTIES:
        assert f'<option value="{value}">' in html
    assert html.count('class="part"') == 6  # one body part per wrong guess
    resp.close()


@pytest.mark.parametrize("path,mimetype", [
    ("/static/style.css", "text/css"),
    ("/static/app.js", "text/javascript"),
    ("/static/index.html", "text/html"),
])
def test_static_files_are_served(client, path, mimetype):
    resp = client.get(path)
    assert resp.status_code == 200
    assert resp.mimetype == mimetype
    assert len(resp.get_data()) > 100
    resp.close()


def test_page_references_files_that_exist(client):
    html = client.get("/").get_data(as_text=True)
    refs = re.findall(r'(?:href|src)="(/static/[^"]+)"', html)
    assert set(refs) == {"/static/style.css", "/static/app.js"}
    for ref in refs:
        resp = client.get(ref)
        assert resp.status_code == 200
        resp.close()


def test_missing_static_file_is_json_404(client):
    resp = client.get("/static/nothing.js")
    assert resp.status_code == 404
    assert resp.get_json()["error"]


def test_static_files_cannot_escape_the_static_folder(client):
    for path in ("/static/../server.py", "/static/..%2fserver.py", "/static/%2e%2e/game.py"):
        assert client.get(path).status_code in (404, 400)


def test_root_only_allows_get(client):
    resp = client.post("/")
    assert resp.status_code == 405
    assert resp.get_json()["error"]


def test_api_routes_still_work_next_to_the_page(client):
    assert client.post("/api/games", json={"difficulty": "easy"}).status_code == 201
    assert client.get("/api/games/nope").status_code == 404


# ---- the JavaScript must stay a thin client ----------------------------------

@pytest.fixture(scope="module")
def app_js():
    return (STATIC / "app.js").read_text(encoding="utf-8")


def test_js_uses_fetch_with_relative_api_urls(app_js):
    assert "fetch(" in app_js
    assert '"/api/games"' in app_js
    assert "http://" not in app_js and "https://" not in app_js and "localhost" not in app_js


def test_js_contains_no_word_lists(app_js):
    # UI strings like "button" happen to be real words, so look for the shape of an embedded
    # list instead: many consecutive quoted words, or a long run of real words as literals.
    assert not re.search(r"""(?:["'`][a-z]+["'`]\s*,\s*){10,}""", app_js.lower())
    all_words = {w for d in DIFFICULTIES for w in WordManager().words(d)}
    quoted = set(re.findall(r"""["'`]([a-z]+)["'`]""", app_js.lower()))
    assert len(quoted & all_words) < 10
    assert len(app_js) < 20_000


def test_js_does_not_implement_game_rules(app_js):
    # No local max-guess constant or win/loss decision: those come from the server's `status`.
    assert not re.search(r"\b(maxWrong|MAX_WRONG|maxGuesses|MAX_GUESSES|secretWord|hiddenWord)\b", app_js)
    assert "game.status" in app_js and "game.word" in app_js
