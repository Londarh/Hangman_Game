import json

import pytest

import server
from server import create_app


class FixedWords:
    """Stand-in word manager: always returns the same word per difficulty."""

    def __init__(self, **words):
        self.words = {"easy": "cat", "medium": "planet", "hard": "architecture", **words}
        self.requested = []

    def random_word(self, difficulty):
        self.requested.append(difficulty)
        return self.words[difficulty]


@pytest.fixture
def words():
    return FixedWords()


@pytest.fixture
def client(words):
    return create_app(words).test_client()


def create(client, difficulty="easy"):
    resp = client.post("/api/games", json={"difficulty": difficulty})
    assert resp.status_code == 201
    return resp.get_json()


def guess(client, game_id, letter):
    return client.post(f"/api/games/{game_id}/guess", json={"letter": letter})


def assert_json_error(resp, status):
    assert resp.status_code == status
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    assert set(body) == {"error"} and isinstance(body["error"], str) and body["error"]


# ---- module-level app -------------------------------------------------------

def test_module_level_app_exists_for_gunicorn():
    assert server.app.name and callable(server.app)
    assert server.app.test_client().post("/api/games", json={"difficulty": "easy"}).status_code == 201


# ---- create -----------------------------------------------------------------

def test_create_game_returns_201_and_full_state(client):
    data = create(client)
    assert data["pattern"] == "_ _ _"
    assert data["guessed_letters"] == []
    assert data["incorrect_letters"] == []
    assert data["remaining_guesses"] == 6
    assert data["status"] == "playing"
    assert isinstance(data["game_id"], str) and len(data["game_id"]) >= 32


@pytest.mark.parametrize("difficulty,pattern", [("easy", "_ _ _"), ("medium", "_ _ _ _ _ _"), ("hard", "_ " * 11 + "_")])
def test_create_all_difficulties(client, words, difficulty, pattern):
    assert create(client, difficulty)["pattern"] == pattern
    assert words.requested == [difficulty]


def test_difficulty_is_case_insensitive(client, words):
    create(client, "Hard")
    assert words.requested == ["hard"]


def test_game_ids_are_unique(client):
    ids = {create(client)["game_id"] for _ in range(50)}
    assert len(ids) == 50


@pytest.mark.parametrize("body", [{}, {"difficulty": None}, {"difficulty": "extreme"}, {"difficulty": ""},
                                  {"difficulty": 1}, {"difficulty": ["easy"]}, {"level": "easy"}])
def test_create_rejects_missing_or_invalid_difficulty(client, body):
    assert_json_error(client.post("/api/games", json=body), 400)


@pytest.mark.parametrize("raw", [b"", b"not json", b"{bad", b"[]", b'"easy"', b"5", b"null", b"[1, 2]"])
def test_create_rejects_non_object_bodies(client, raw):
    resp = client.post("/api/games", data=raw, content_type="application/json")
    assert_json_error(resp, 400)


def test_create_with_no_body_or_content_type(client):
    assert_json_error(client.post("/api/games"), 400)
    assert_json_error(client.post("/api/games", data="difficulty=easy"), 400)


# ---- get --------------------------------------------------------------------

def test_get_game_returns_current_state(client):
    created = create(client)
    guess(client, created["game_id"], "c")
    resp = client.get(f"/api/games/{created['game_id']}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["game_id"] == created["game_id"]
    assert data["pattern"] == "c _ _"
    assert data["guessed_letters"] == ["c"]


def test_get_unknown_game_is_404(client):
    assert_json_error(client.get("/api/games/doesnotexist"), 404)


# ---- guess ------------------------------------------------------------------

def test_correct_guess(client):
    game_id = create(client)["game_id"]
    resp = guess(client, game_id, "a")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["pattern"] == "_ a _"
    assert data["guessed_letters"] == ["a"]
    assert data["incorrect_letters"] == []
    assert data["remaining_guesses"] == 6
    assert data["status"] == "playing"
    assert data["game_id"] == game_id


def test_incorrect_guess(client):
    game_id = create(client)["game_id"]
    data = guess(client, game_id, "z").get_json()
    assert data["incorrect_letters"] == ["z"]
    assert data["remaining_guesses"] == 5
    assert data["pattern"] == "_ _ _"


def test_uppercase_guess_works(client):
    game_id = create(client)["game_id"]
    assert guess(client, game_id, "C").get_json()["pattern"] == "c _ _"


def test_full_game_win(client):
    game_id = create(client)["game_id"]
    for letter in "cat":
        resp = guess(client, game_id, letter)
        assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "won"
    assert data["pattern"] == "c a t"
    assert data["word"] == "cat"
    assert client.get(f"/api/games/{game_id}").get_json()["word"] == "cat"


def test_full_game_loss(client):
    game_id = create(client)["game_id"]
    for i, letter in enumerate("zqxjkv", start=1):
        data = guess(client, game_id, letter).get_json()
        assert data["remaining_guesses"] == 6 - i
        assert data["status"] == ("lost" if i == 6 else "playing")
    assert data["word"] == "cat"
    assert data["incorrect_letters"] == list("zqxjkv")


def test_duplicate_guess_is_400_and_changes_nothing(client):
    game_id = create(client)["game_id"]
    guess(client, game_id, "z")
    before = client.get(f"/api/games/{game_id}").get_json()
    for letter in ("z", "Z"):
        assert_json_error(guess(client, game_id, letter), 400)
    assert client.get(f"/api/games/{game_id}").get_json() == before


@pytest.mark.parametrize("outcome", ["won", "lost"])
def test_guess_after_game_over_is_409_and_changes_nothing(client, outcome):
    game_id = create(client)["game_id"]
    for letter in ("cat" if outcome == "won" else "zqxjkv"):
        guess(client, game_id, letter)
    before = client.get(f"/api/games/{game_id}").get_json()
    assert before["status"] == outcome
    assert_json_error(guess(client, game_id, "b"), 409)
    assert_json_error(guess(client, game_id, "c"), 409)
    assert client.get(f"/api/games/{game_id}").get_json() == before


def test_guess_unknown_game_is_404(client):
    assert_json_error(guess(client, "doesnotexist", "a"), 404)


@pytest.mark.parametrize("body", [{}, {"letters": "a"}, {"letter": None}])
def test_guess_missing_letter(client, body):
    game_id = create(client)["game_id"]
    resp = client.post(f"/api/games/{game_id}/guess", json=body)
    assert_json_error(resp, 400)


@pytest.mark.parametrize("letter", [5, 1.5, True, ["a"], {"a": 1}, None])
def test_guess_letter_must_be_a_string(client, letter):
    game_id = create(client)["game_id"]
    assert_json_error(guess(client, game_id, letter), 400)


@pytest.mark.parametrize("letter", ["", "ab", "1", " ", "!", "é"])
def test_guess_letter_must_be_a_single_letter(client, letter):
    game_id = create(client)["game_id"]
    assert_json_error(guess(client, game_id, letter), 400)
    assert client.get(f"/api/games/{game_id}").get_json()["guessed_letters"] == []


@pytest.mark.parametrize("raw", [b"", b"nope", b"[]", b'"a"', b"7"])
def test_guess_rejects_non_object_bodies(client, raw):
    game_id = create(client)["game_id"]
    resp = client.post(f"/api/games/{game_id}/guess", data=raw, content_type="application/json")
    assert_json_error(resp, 400)


def test_guess_with_no_body(client):
    game_id = create(client)["game_id"]
    assert_json_error(client.post(f"/api/games/{game_id}/guess"), 400)


# ---- isolation --------------------------------------------------------------

def test_two_games_do_not_affect_each_other():
    client = create_app(FixedWords(easy="cat", medium="planet")).test_client()
    a = create(client, "easy")["game_id"]
    b = create(client, "medium")["game_id"]
    guess(client, a, "c")
    guess(client, a, "z")
    guess(client, b, "p")
    state_a = client.get(f"/api/games/{a}").get_json()
    state_b = client.get(f"/api/games/{b}").get_json()
    assert state_a["pattern"] == "c _ _" and state_a["remaining_guesses"] == 5
    assert state_b["pattern"] == "p _ _ _ _ _" and state_b["remaining_guesses"] == 6
    for letter in "qxjkv":  # with the earlier "z", six wrong guesses in game a
        guess(client, a, letter)
    assert client.get(f"/api/games/{a}").get_json()["status"] == "lost"
    assert client.get(f"/api/games/{b}").get_json()["status"] == "playing"


def test_separate_apps_do_not_share_games(words):
    one, two = create_app(words).test_client(), create_app(words).test_client()
    game_id = create(one)["game_id"]
    assert_json_error(two.get(f"/api/games/{game_id}"), 404)


# ---- hidden word ------------------------------------------------------------

def test_word_never_in_any_response_while_playing():
    word = "zebra"
    client = create_app(FixedWords(easy=word)).test_client()
    created = create(client)
    game_id = created["game_id"]
    responses = [client.post("/api/games", json={"difficulty": "easy"}), client.get(f"/api/games/{game_id}")]
    for letter in "zebq":  # reveals most of the word, but not all of it
        responses.append(guess(client, game_id, letter))
    responses += [guess(client, game_id, "z"), guess(client, game_id, "!"), guess(client, game_id, 5),
                  client.get(f"/api/games/{game_id}"), client.get("/api/games/nope")]
    for resp in responses:
        assert word not in resp.get_data(as_text=True)
        assert "word" not in (resp.get_json() or {}) or resp.get_json()["status"] != "playing"
    assert client.get(f"/api/games/{game_id}").get_json()["status"] == "playing"
    for letter in "ra":
        resp = guess(client, game_id, letter)
    assert resp.get_json()["status"] == "won" and resp.get_json()["word"] == word


def test_no_answer_fields_while_playing(client):
    data = create(client)
    assert set(data) == {"game_id", "pattern", "guessed_letters", "incorrect_letters",
                         "remaining_guesses", "status"}


# ---- JSON for everything ----------------------------------------------------

def test_unknown_url_is_json_404(client):
    assert_json_error(client.get("/nope"), 404)
    assert_json_error(client.get("/api/unknown"), 404)


@pytest.mark.parametrize("method,url", [("get", "/api/games"), ("put", "/api/games"),
                                        ("delete", "/api/games/abc"), ("post", "/api/games/abc"),
                                        ("get", "/api/games/abc/guess")])
def test_wrong_method_is_json_405(client, method, url):
    resp = getattr(client, method)(url)
    assert_json_error(resp, 405)
    assert "Allow" in resp.headers


def test_unexpected_exception_returns_json_500():
    class Broken:
        def random_word(self, difficulty):
            raise RuntimeError("secret internal detail")

    app = create_app(Broken())
    app.config["PROPAGATE_EXCEPTIONS"] = False
    resp = app.test_client().post("/api/games", json={"difficulty": "easy"})
    assert_json_error(resp, 500)
    assert "secret internal detail" not in resp.get_data(as_text=True)


def test_success_responses_are_json(client):
    created = client.post("/api/games", json={"difficulty": "easy"})
    game_id = created.get_json()["game_id"]
    for resp in (created, client.get(f"/api/games/{game_id}"), guess(client, game_id, "c")):
        assert resp.mimetype == "application/json"
        json.loads(resp.get_data(as_text=True))


# ---- real word lists --------------------------------------------------------

def test_default_app_uses_real_word_lists():
    client = server.app.test_client()
    for difficulty in ("easy", "medium", "hard"):
        data = client.post("/api/games", json={"difficulty": difficulty}).get_json()
        assert data["status"] == "playing" and "_" in data["pattern"]
