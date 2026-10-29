"""Flask REST API for Hangman. All game rules live in game.py and word_manager.py."""

import os
import uuid

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from game import GameOverError, HangmanGame, InvalidGuessError
from word_manager import InvalidDifficultyError, WordManager, normalize_difficulty


def error_response(message, status):
    return jsonify({"error": message}), status


def create_app(word_manager=None):
    app = Flask(__name__)
    words = word_manager if word_manager is not None else WordManager()
    games = {}

    def json_body():
        body = request.get_json(force=True, silent=True)
        if not isinstance(body, dict):
            return None
        return body

    def game_state(game_id, game):
        return {"game_id": game_id, **game.to_state()}

    @app.post("/api/games")
    def create_game():
        body = json_body()
        if body is None:
            return error_response("request body must be a JSON object", 400)
        if "difficulty" not in body:
            return error_response("difficulty is required (easy, medium or hard)", 400)
        try:
            difficulty = normalize_difficulty(body["difficulty"])
        except InvalidDifficultyError as exc:
            return error_response(str(exc), 400)
        game_id = uuid.uuid4().hex
        games[game_id] = HangmanGame(words.random_word(difficulty))
        return jsonify(game_state(game_id, games[game_id])), 201

    @app.get("/api/games/<game_id>")
    def get_game(game_id):
        game = games.get(game_id)
        if game is None:
            return error_response("game not found", 404)
        return jsonify(game_state(game_id, game))

    @app.post("/api/games/<game_id>/guess")
    def guess(game_id):
        game = games.get(game_id)
        if game is None:
            return error_response("game not found", 404)
        body = json_body()
        if body is None:
            return error_response("request body must be a JSON object", 400)
        if "letter" not in body:
            return error_response("letter is required", 400)
        if not isinstance(body["letter"], str):
            return error_response("letter must be a string", 400)
        try:
            game.guess(body["letter"])
        except GameOverError as exc:
            return error_response(str(exc), 409)
        except InvalidGuessError as exc:
            return error_response(str(exc), 400)
        return jsonify(game_state(game_id, game))

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        response, status = error_response(exc.description or exc.name, exc.code)
        for name, value in exc.get_headers():  # keep e.g. Allow on 405
            if name.lower() not in ("content-type", "content-length"):
                response.headers[name] = value
        return response, status

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        app.logger.exception("unhandled error")
        return error_response("internal server error", 500)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
