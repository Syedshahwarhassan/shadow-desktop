"""
AntiGravity Web — A browser-based JARVIS-style HUD that wraps the AntiGravity
voice assistant for environments without a desktop (Replit/Linux containers).

The original PyQt6 desktop application (main.py, hud.py, listener.py, tray.py)
is preserved untouched. This file provides a Flask-based alternative that uses
the browser's Web Speech API for microphone input and TTS output, while reusing
the project's existing AI brain and memory manager.
"""

import os
import re
import json
import time
import math
import platform
from datetime import datetime

import psutil
import requests
import pyjokes
import wikipedia
from flask import Flask, render_template, request, jsonify, send_from_directory
from sympy import sympify, SympifyError

from config_manager import config_manager
from memory_manager import memory_manager
from ai_brain import ai_brain


app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_AS_ASCII"] = False


# ─────────────────────────────────────────────────────────────────────────────
# Conversation history (in-memory ring buffer)
# ─────────────────────────────────────────────────────────────────────────────
HISTORY_MAX = 200
_history: list[dict] = []


def _push_history(role: str, text: str) -> None:
    _history.append({
        "role": role,
        "text": text,
        "ts": datetime.utcnow().isoformat() + "Z",
    })
    if len(_history) > HISTORY_MAX:
        del _history[: len(_history) - HISTORY_MAX]


# ─────────────────────────────────────────────────────────────────────────────
# Skill: weather (free, no API key — wttr.in)
# ─────────────────────────────────────────────────────────────────────────────
def skill_weather(city: str) -> str:
    city = (city or "Lahore").strip() or "Lahore"
    try:
        r = requests.get(
            f"https://wttr.in/{city}",
            params={"format": "j1"},
            timeout=8,
            headers={"User-Agent": "AntiGravity-Web"},
        )
        r.raise_for_status()
        data = r.json()
        cur = data["current_condition"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp_c = cur["temp_C"]
        feels = cur["FeelsLikeC"]
        humidity = cur["humidity"]
        wind = cur["windspeedKmph"]
        return (
            f"{city.title()}: {desc}, {temp_c}°C (feels like {feels}°C). "
            f"Humidity {humidity}%, wind {wind} km/h."
        )
    except Exception as e:
        return f"Couldn't fetch weather for {city}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Skill: wikipedia summary
# ─────────────────────────────────────────────────────────────────────────────
def skill_wikipedia(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return "Please tell me what to look up on Wikipedia."
    try:
        return wikipedia.summary(query, sentences=3, auto_suggest=True)
    except wikipedia.DisambiguationError as e:
        opts = ", ".join(e.options[:5])
        return f"That term is ambiguous. Try one of: {opts}."
    except Exception as e:
        return f"Couldn't find a Wikipedia article: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Skill: calculator (sympy — safe expression evaluation)
# ─────────────────────────────────────────────────────────────────────────────
def skill_calculate(expr: str) -> str:
    expr = (expr or "").strip()
    if not expr:
        return "Please give me an expression to evaluate."
    cleaned = (
        expr.lower()
        .replace("plus", "+")
        .replace("minus", "-")
        .replace("times", "*")
        .replace("multiplied by", "*")
        .replace("divided by", "/")
        .replace("over", "/")
        .replace("x", "*")
        .replace("^", "**")
    )
    cleaned = re.sub(r"[^0-9+\-*/().% \t**]", "", cleaned)
    if not cleaned:
        return "I couldn't parse that expression."
    try:
        result = sympify(cleaned).evalf()
        return f"{expr} = {result}"
    except (SympifyError, Exception) as e:
        return f"Calculation error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Skill: currency conversion (free — exchangerate.host)
# ─────────────────────────────────────────────────────────────────────────────
def skill_currency(amount: float, src: str, dst: str) -> str:
    try:
        src = (src or "USD").upper()
        dst = (dst or "PKR").upper()
        r = requests.get(
            "https://open.er-api.com/v6/latest/" + src, timeout=8
        )
        r.raise_for_status()
        data = r.json()
        rate = data.get("rates", {}).get(dst)
        if rate is None:
            return f"Couldn't find rate {src} → {dst}."
        converted = amount * rate
        return f"{amount:g} {src} = {converted:,.2f} {dst}"
    except Exception as e:
        return f"Currency conversion failed: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Skill: jokes & quotes
# ─────────────────────────────────────────────────────────────────────────────
def skill_joke() -> str:
    try:
        return pyjokes.get_joke()
    except Exception:
        return "Why did the developer go broke? Because they used up all their cache."


_QUOTES = [
    "The best way to predict the future is to invent it. — Alan Kay",
    "Stay hungry, stay foolish. — Steve Jobs",
    "Code is like humor. When you have to explain it, it's bad. — Cory House",
    "First, solve the problem. Then, write the code. — John Johnson",
    "Simplicity is the soul of efficiency. — Austin Freeman",
    "Make it work, make it right, make it fast. — Kent Beck",
    "Talk is cheap. Show me the code. — Linus Torvalds",
    "Programs must be written for people to read. — Hal Abelson",
]


def skill_quote() -> str:
    import random
    return random.choice(_QUOTES)


# ─────────────────────────────────────────────────────────────────────────────
# Skill: server / system info
# ─────────────────────────────────────────────────────────────────────────────
def skill_system_info() -> str:
    cpu = psutil.cpu_percent(interval=0.4)
    ram = psutil.virtual_memory()
    uname = platform.uname()
    return (
        f"Host: {uname.system} {uname.release}. "
        f"CPU at {cpu}%. "
        f"RAM {ram.percent}% used ({ram.used // (1024**2)} MB / "
        f"{ram.total // (1024**2)} MB)."
    )


def get_live_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0.0)
    ram = psutil.virtual_memory()
    return {
        "cpu": cpu,
        "ram_percent": ram.percent,
        "ram_used_mb": ram.used // (1024 ** 2),
        "ram_total_mb": ram.total // (1024 ** 2),
        "now": datetime.now().strftime("%I:%M:%S %p"),
        "date": datetime.now().strftime("%A, %B %d, %Y"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Skill: time / date
# ─────────────────────────────────────────────────────────────────────────────
def skill_time() -> str:
    return f"It's {datetime.now().strftime('%I:%M %p')}."


def skill_date() -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."


# ─────────────────────────────────────────────────────────────────────────────
# Skill: memory / notes
# ─────────────────────────────────────────────────────────────────────────────
def skill_remember(note: str) -> str:
    note = (note or "").strip()
    if not note:
        return "What should I remember?"
    memory_manager.add_note(note)
    return f"Saved to long-term memory: {note}"


def skill_list_memory() -> str:
    notes = memory_manager.memory.get("notes", [])
    if not notes:
        return "Your long-term memory is empty."
    return "I remember: " + "; ".join(notes)


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher — converts free-form text → skill response
# ─────────────────────────────────────────────────────────────────────────────
def dispatch(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "I didn't catch that."
    t = raw.lower()

    # Greetings / identity
    if re.fullmatch(r"(hi|hello|hey|salaam|salam|assalam.*)\W*", t):
        name = config_manager.get("assistant_name", "Shadow")
        return f"Hello! I'm {name}. How can I help?"

    if any(k in t for k in ["who are you", "your name", "introduce yourself"]):
        name = config_manager.get("assistant_name", "Shadow")
        return f"I'm {name}, your web-based JARVIS-style assistant."

    # Time / date
    if any(k in t for k in ["what time", "current time", "time now", "the time"]):
        return skill_time()
    if "date" in t or "today" in t:
        return skill_date()

    # Memory
    if t.startswith(("remember ", "remember that ", "note that ", "note ")):
        note = re.sub(r"^(remember that |remember |note that |note )", "", t).strip()
        return skill_remember(note)
    if any(k in t for k in ["what do you remember", "list memory", "show notes", "my notes"]):
        return skill_list_memory()

    # Weather
    if "weather" in t or "mausam" in t:
        m = re.search(r"(?:weather|mausam)(?:\s+(?:in|of|for))?\s+(.+)", t)
        city = m.group(1).strip() if m else config_manager.get("default_city", "Lahore")
        return skill_weather(city)

    # Wikipedia
    if t.startswith(("wiki ", "wikipedia ")) or "tell me about " in t or "who is " in t or "what is " in t:
        q = re.sub(r"^(wiki|wikipedia|tell me about|who is|what is)\s+", "", t).strip("?. ")
        return skill_wikipedia(q)

    # Calculator
    if t.startswith(("calc ", "calculate ", "compute ", "what is ")) or re.search(r"\d\s*[\+\-\*/x^]\s*\d", t):
        expr = re.sub(r"^(calc|calculate|compute|what is)\s+", "", t).strip("?")
        return skill_calculate(expr)

    # Currency
    m = re.search(r"convert\s+([\d.]+)\s+([a-z]{3})\s+(?:to|in|into)\s+([a-z]{3})", t)
    if m:
        return skill_currency(float(m.group(1)), m.group(2), m.group(3))

    # Jokes / quotes
    if any(k in t for k in ["joke", "funny", "latifa", "mazak", "make me laugh"]):
        return skill_joke()
    if any(k in t for k in ["quote", "motivation", "inspire", "aqwal"]):
        return skill_quote()

    # System info
    if any(k in t for k in ["system info", "server stats", "cpu", "ram", "memory usage"]):
        return skill_system_info()

    # AI fallback
    try:
        return ai_brain.get_response(raw)
    except Exception as e:
        return f"AI core error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.after_request
def _no_cache(resp):
    if os.environ.get("FLASK_ENV") != "production":
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@app.route("/")
def index():
    return render_template(
        "index.html",
        assistant_name=config_manager.get("assistant_name", "Shadow"),
        wake_word=config_manager.get("wake_word", "shadow"),
        theme_color=config_manager.get("hud.theme_color", "#00D4FF"),
    )


@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "empty input"}), 400
    _push_history("user", text)
    response = dispatch(text)
    _push_history("assistant", response)
    return jsonify({"ok": True, "response": response})


@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify({"ok": True, "history": _history[-50:]})


@app.route("/api/history", methods=["DELETE"])
def api_clear_history():
    _history.clear()
    return jsonify({"ok": True})


@app.route("/api/stats")
def api_stats():
    return jsonify(get_live_stats())


@app.route("/api/memory", methods=["GET"])
def api_memory_list():
    return jsonify({"notes": memory_manager.memory.get("notes", [])})


@app.route("/api/memory", methods=["POST"])
def api_memory_add():
    data = request.get_json(silent=True) or {}
    note = (data.get("note") or "").strip()
    if not note:
        return jsonify({"ok": False, "error": "empty note"}), 400
    memory_manager.add_note(note)
    return jsonify({"ok": True})


@app.route("/api/memory", methods=["DELETE"])
def api_memory_clear():
    memory_manager.memory["notes"] = []
    memory_manager.save_memory()
    return jsonify({"ok": True})


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
