// Hangman browser client.
//
// All game rules live on the server. This file only:
//   1. sends requests to the REST API with fetch(), and
//   2. draws whatever game state the server sends back.
// It never knows the hidden word until the server reveals it after a win/loss.

const GAMES_URL = "/api/games"; // relative URL: works wherever the site is hosted
const LETTERS = "abcdefghijklmnopqrstuvwxyz";

const els = {
  difficulty: document.getElementById("difficulty"),
  newGame: document.getElementById("new-game"),
  pattern: document.getElementById("pattern"),
  remaining: document.getElementById("remaining"),
  guessed: document.getElementById("guessed"),
  wrong: document.getElementById("wrong"),
  message: document.getElementById("message"),
  error: document.getElementById("error"),
  keyboard: document.getElementById("keyboard"),
  parts: document.querySelectorAll("#hangman .part"),
};

let game = null;      // latest state received from the server
let guessing = false; // true while a guess request is in flight
const queue = [];     // letters typed while a request was in flight, sent in order
let startToken = 0;   // lets us ignore the reply of an outdated "new game" request

// ---------------------------------------------------------------------------
// Talking to the server
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status; // HTTP status, or 0 if the server could not be reached
  }
}

// Send one request and return the parsed JSON body.
// The browser sends   method + URL + JSON body   over HTTP,
// Flask handles it and replies with JSON, and we turn that reply into an object.
async function api(method, url, body) {
  let response;
  try {
    response = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (networkError) {
    // fetch() only rejects when no response arrived at all (offline, server down...)
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  }

  let data = null;
  try {
    data = await response.json();
  } catch (notJson) {
    // keep data = null; handled below
  }

  if (!response.ok) {
    // The server explains errors as {"error": "message"}
    throw new ApiError((data && data.error) || "Server error (" + response.status + ").", response.status);
  }
  return data;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function startGame() {
  const token = ++startToken;
  guessing = false;
  queue.length = 0;
  try {
    // POST /api/games  with  {"difficulty": "easy"}  ->  new game state
    const state = await api("POST", GAMES_URL, { difficulty: els.difficulty.value });
    if (token !== startToken) return; // a newer "new game" click replaced this one
    game = state;
    showError(null);
    render();
  } catch (err) {
    if (token === startToken) showError(err.message);
  }
}

async function guessLetter(letter) {
  // Ignore the guess if there is no running game, the letter was already used,
  // or it is already waiting in the queue (stops double-click duplicates).
  if (!game || game.status !== "playing" || game.guessed_letters.includes(letter) || queue.includes(letter)) return;

  queue.push(letter);
  if (guessing) return; // a request is in flight; the loop below will send this letter next

  const gameId = game.game_id;
  guessing = true;
  updateKeyboard();
  try {
    // Send queued letters one at a time, so fast typing is not lost and requests never overlap.
    while (queue.length > 0 && game && game.game_id === gameId && game.status === "playing") {
      const next = queue.shift();
      if (game.guessed_letters.includes(next)) continue;
      // POST /api/games/<id>/guess  with  {"letter": "e"}  ->  updated game state
      const state = await api("POST", GAMES_URL + "/" + gameId + "/guess", { letter: next });
      if (!game || game.game_id !== gameId) return; // player started a new game meanwhile
      game = state;
      showError(null);
      render();
    }
  } catch (err) {
    if (!game || game.game_id !== gameId) return;
    if (err.status === 404) {
      // e.g. the server restarted and forgot this game
      game = null;
      render();
      showError("This game no longer exists on the server. Press New Game to start again.");
    } else {
      showError(err.message);
    }
  } finally {
    if (game && game.game_id === gameId) {
      queue.length = 0;
      guessing = false;
      updateKeyboard();
    }
  }
}

// ---------------------------------------------------------------------------
// Drawing the state
// ---------------------------------------------------------------------------

function showError(text) {
  els.error.hidden = !text;
  els.error.textContent = text || "";
}

function render() {
  if (!game) {
    els.pattern.textContent = " ";
    els.remaining.textContent = "-";
    els.guessed.textContent = "-";
    els.wrong.textContent = "-";
    els.message.textContent = "";
    els.message.dataset.state = "";
    els.parts.forEach((part) => part.classList.remove("shown"));
    updateKeyboard();
    return;
  }

  els.pattern.textContent = game.pattern;
  els.pattern.setAttribute("aria-label", game.pattern.replace(/_/g, "blank"));
  els.remaining.textContent = game.remaining_guesses;
  els.guessed.textContent = game.guessed_letters.join(", ") || "-";
  els.wrong.textContent = game.incorrect_letters.join(", ") || "-";

  // One body part per wrong guess (parts are listed in drawing order in index.html)
  els.parts.forEach((part, i) => part.classList.toggle("shown", i < game.incorrect_letters.length));

  els.message.dataset.state = game.status;
  if (game.status === "won") {
    els.message.textContent = "You won! The word was “" + game.word + "”.";
  } else if (game.status === "lost") {
    els.message.textContent = "You lost. The word was “" + game.word + "”.";
  } else {
    els.message.textContent = "Pick a letter.";
  }

  updateKeyboard();
  if (game.status !== "playing") els.newGame.focus(); // Enter then starts another game
}

function buildKeyboard() {
  for (const letter of LETTERS) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = letter;
    button.dataset.letter = letter;
    button.setAttribute("aria-label", "Guess " + letter);
    button.addEventListener("click", () => guessLetter(letter));
    els.keyboard.appendChild(button);
  }
}

// A key is disabled when its letter was already guessed, the game is over, or a request is pending.
function updateKeyboard() {
  for (const button of els.keyboard.children) {
    const letter = button.dataset.letter;
    const used = game !== null && game.guessed_letters.includes(letter);
    button.disabled = !game || game.status !== "playing" || guessing || used;
    button.classList.toggle("correct", used && !game.incorrect_letters.includes(letter));
    button.classList.toggle("incorrect", used && game.incorrect_letters.includes(letter));
  }
}

// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------

els.newGame.addEventListener("click", startGame);

// Physical keyboard: a single a-z key guesses that letter.
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) return;
  if (event.target.tagName === "SELECT") return; // typing in the dropdown just picks an option
  const letter = event.key.toLowerCase();
  if (letter.length === 1 && LETTERS.includes(letter)) guessLetter(letter);
});

buildKeyboard();
render();
startGame(); // begin a game right away using the default difficulty
