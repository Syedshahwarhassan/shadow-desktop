"""
extra_cmds.py — Cross-platform feature pack for AntiGravity.

These commands have **no Windows-only dependencies** so they work identically
on Windows, macOS and Linux. They're wired into the main dispatcher in
`commands/__init__.py`.

Features:
  - WikipediaCommands : "tell me about Einstein", "wiki Eiffel Tower"
  - CalculatorCommands: "calculate 23 * 47 + 12", "what is sqrt(144)"
  - CurrencyCommands  : "convert 100 USD to PKR"
  - UnitCommands      : "convert 10 km to miles"
  - PasswordCommands  : "generate password", "generate password 24"
  - TimerCommands     : "set timer for 5 minutes", "set alarm for 2 minutes"
  - FunCommands       : "flip a coin", "roll a dice", "random fact"
  - NewsCommands      : "give me the news" (uses NewsAPI key if present)
"""

from __future__ import annotations

import os
import re
import math
import random
import secrets
import string
import threading
from datetime import datetime, timedelta

import requests


# ─────────────────────────────────────────────────────────────────────────────
# Wikipedia
# ─────────────────────────────────────────────────────────────────────────────
class WikipediaCommands:
    @staticmethod
    def summary(query: str, sentences: int = 3) -> str:
        query = (query or "").strip()
        if not query:
            return "Please tell me what to look up."
        try:
            import wikipedia  # type: ignore
        except ImportError:
            return "Wikipedia module not installed. Run: pip install wikipedia"
        try:
            return wikipedia.summary(query, sentences=sentences, auto_suggest=True)
        except wikipedia.DisambiguationError as e:  # type: ignore[attr-defined]
            options = ", ".join(e.options[:5])
            return f"That term is ambiguous. Try one of: {options}."
        except wikipedia.PageError:  # type: ignore[attr-defined]
            return f"I couldn't find a Wikipedia article for '{query}'."
        except Exception as e:
            return f"Wikipedia lookup failed: {e}"

    @staticmethod
    def search(query: str, limit: int = 5) -> str:
        try:
            import wikipedia  # type: ignore
            results = wikipedia.search(query, results=limit)
            if not results:
                return f"No Wikipedia results for '{query}'."
            return "Top results: " + "; ".join(results)
        except Exception as e:
            return f"Search failed: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Calculator (safe math via sympy)
# ─────────────────────────────────────────────────────────────────────────────
class CalculatorCommands:
    _WORD_OPS = {
        "plus": "+", "added to": "+", "and": "+",
        "minus": "-", "less": "-", "subtract": "-",
        "times": "*", "multiplied by": "*", "x": "*",
        "divided by": "/", "over": "/",
        "to the power of": "**", "power": "**", "^": "**",
        "modulo": "%", "mod": "%",
    }

    @staticmethod
    def _normalize(expr: str) -> str:
        e = expr.lower()
        # longest first to avoid "added" before "added to"
        for word, op in sorted(CalculatorCommands._WORD_OPS.items(), key=lambda x: -len(x[0])):
            e = e.replace(word, op)
        # keep digits, basic operators, parens, decimal, percent and whitespace
        return re.sub(r"[^0-9+\-*/().% \t]", "", e).strip()

    @staticmethod
    def evaluate(expr: str) -> str:
        expr = (expr or "").strip()
        if not expr:
            return "Please give me an expression."
        cleaned = CalculatorCommands._normalize(expr)
        if not cleaned:
            return "I couldn't parse that expression."
        try:
            from sympy import sympify  # type: ignore
            result = sympify(cleaned).evalf()
            # prettify integers
            try:
                if float(result).is_integer():
                    result = int(float(result))
            except Exception:
                pass
            return f"{expr} = {result}"
        except Exception as e:
            return f"Calculation error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Currency (free, no API key — open.er-api.com)
# ─────────────────────────────────────────────────────────────────────────────
class CurrencyCommands:
    _SYMBOL_HINTS = {
        "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY",
        "₹": "INR", "₨": "PKR", "rs": "PKR", "rupees": "PKR",
        "dollars": "USD", "dollar": "USD", "euros": "EUR", "euro": "EUR",
        "pounds": "GBP", "yen": "JPY",
    }

    @staticmethod
    def convert(amount: float, src: str, dst: str) -> str:
        try:
            src = (src or "USD").upper()
            dst = (dst or "PKR").upper()
            url = f"https://open.er-api.com/v6/latest/{src}"
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            data = r.json()
            rate = data.get("rates", {}).get(dst)
            if rate is None:
                return f"I don't have a rate for {src} → {dst}."
            converted = float(amount) * float(rate)
            return f"{float(amount):g} {src} is approximately {converted:,.2f} {dst}."
        except Exception as e:
            return f"Currency conversion failed: {e}"

    @staticmethod
    def parse_and_convert(text: str) -> str | None:
        """Parse 'convert 100 USD to PKR' style commands."""
        m = re.search(
            r"(?:convert\s+)?([\d.,]+)\s*([a-z$€£¥₹₨]{1,8})\s+(?:to|into|in)\s+([a-z$€£¥₹₨]{1,8})",
            text.lower(),
        )
        if not m:
            return None
        amt = float(m.group(1).replace(",", ""))
        src = CurrencyCommands._SYMBOL_HINTS.get(m.group(2).strip(), m.group(2).upper())
        dst = CurrencyCommands._SYMBOL_HINTS.get(m.group(3).strip(), m.group(3).upper())
        return CurrencyCommands.convert(amt, src, dst)


# ─────────────────────────────────────────────────────────────────────────────
# Units (pint)
# ─────────────────────────────────────────────────────────────────────────────
class UnitCommands:
    _ureg = None

    @classmethod
    def _registry(cls):
        if cls._ureg is None:
            try:
                from pint import UnitRegistry  # type: ignore
                cls._ureg = UnitRegistry()
            except ImportError:
                cls._ureg = False
        return cls._ureg

    @classmethod
    def convert(cls, amount: float, src_unit: str, dst_unit: str) -> str:
        ureg = cls._registry()
        if not ureg:
            return "Unit conversion needs the 'pint' package: pip install pint"
        try:
            q = ureg.Quantity(float(amount), src_unit)
            converted = q.to(dst_unit)
            mag = converted.magnitude
            # Snap floating-point noise near zero to 0 (e.g. 32°F → 0°C)
            if abs(mag) < 1e-9:
                mag = 0.0
            # Clean numeric display: integers without decimals, otherwise 4 sig figs
            if float(mag).is_integer():
                pretty = f"{int(mag)}"
            else:
                pretty = f"{mag:.4g}"
            return f"{amount} {src_unit} = {pretty} {dst_unit}"
        except Exception as e:
            return f"Unit conversion failed: {e}"

    @classmethod
    def parse_and_convert(cls, text: str) -> str | None:
        """Parse 'convert 10 km to miles' style commands (units, not currency)."""
        m = re.search(
            r"(?:convert\s+)?([\d.]+)\s*([a-z]+)\s+(?:to|into|in)\s+([a-z]+)",
            text.lower(),
        )
        if not m:
            return None
        amt, src, dst = float(m.group(1)), m.group(2), m.group(3)
        # Skip 3-letter currency codes
        if len(src) == 3 and src.isupper():
            return None
        return cls.convert(amt, src, dst)


# ─────────────────────────────────────────────────────────────────────────────
# Password generator
# ─────────────────────────────────────────────────────────────────────────────
class PasswordCommands:
    @staticmethod
    def generate(length: int = 16, symbols: bool = True) -> str:
        length = max(6, min(64, int(length)))
        alphabet = string.ascii_letters + string.digits
        if symbols:
            alphabet += "!@#$%^&*()-_=+[]{}"
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        return f"Generated {length}-char password: {pwd}"


# ─────────────────────────────────────────────────────────────────────────────
# Timer / alarm (threaded — non-blocking)
# ─────────────────────────────────────────────────────────────────────────────
class TimerCommands:
    _timers: list[dict] = []

    @classmethod
    def set_timer(cls, seconds: int, label: str = "", on_fire=None) -> str:
        seconds = max(1, int(seconds))
        label = (label or "").strip() or "timer"
        fires_at = datetime.now() + timedelta(seconds=seconds)

        def _fire():
            print(f"[TIMER] '{label}' fired at {datetime.now().strftime('%H:%M:%S')}")
            if callable(on_fire):
                try:
                    on_fire(f"Time's up for {label}.")
                except Exception as e:
                    print(f"[TIMER] callback error: {e}")

        timer = threading.Timer(seconds, _fire)
        timer.daemon = True
        timer.start()

        cls._timers.append({"label": label, "fires_at": fires_at, "timer": timer})
        return f"Timer set for {seconds} seconds ({label}). Will fire at {fires_at.strftime('%H:%M:%S')}."

    @classmethod
    def list_active(cls) -> str:
        active = [t for t in cls._timers if t["fires_at"] > datetime.now()]
        if not active:
            return "No active timers."
        lines = [
            f"  - {t['label']} → {t['fires_at'].strftime('%H:%M:%S')}"
            for t in active
        ]
        return "Active timers:\n" + "\n".join(lines)

    @staticmethod
    def parse_duration(text: str) -> int | None:
        """Parse '5 minutes', '30 seconds', '1 hour 20 minutes'."""
        total = 0
        found = False
        for value, unit in re.findall(r"(\d+)\s*(hour|hr|minute|min|second|sec)s?", text.lower()):
            v = int(value)
            if unit.startswith("h"):
                total += v * 3600
            elif unit.startswith("m"):
                total += v * 60
            else:
                total += v
            found = True
        return total if found else None


# ─────────────────────────────────────────────────────────────────────────────
# Fun: coin / dice / random fact
# ─────────────────────────────────────────────────────────────────────────────
class FunCommands:
    _FACTS = [
        "Honey never spoils — archaeologists found 3000-year-old honey in Egyptian tombs.",
        "Octopuses have three hearts and blue blood.",
        "Bananas are berries, but strawberries aren't.",
        "A day on Venus is longer than its year.",
        "There are more stars in the universe than grains of sand on Earth.",
        "Sharks existed before trees.",
        "The Eiffel Tower can grow 15 cm taller in the summer.",
        "Wombat poop is cube-shaped.",
        "Your stomach gets a new lining every 3-4 days.",
        "Hot water freezes faster than cold water under certain conditions (the Mpemba effect).",
    ]

    @staticmethod
    def coin_flip() -> str:
        return f"It's {random.choice(['heads', 'tails'])}."

    @staticmethod
    def dice_roll(sides: int = 6, count: int = 1) -> str:
        sides = max(2, int(sides))
        count = max(1, min(20, int(count)))
        rolls = [random.randint(1, sides) for _ in range(count)]
        if count == 1:
            return f"You rolled a {rolls[0]} (d{sides})."
        return f"You rolled {rolls} (sum: {sum(rolls)}) on {count}d{sides}."

    @staticmethod
    def random_fact() -> str:
        return random.choice(FunCommands._FACTS)


# ─────────────────────────────────────────────────────────────────────────────
# News (NewsAPI — optional, only if api_keys.newsapi is set)
# ─────────────────────────────────────────────────────────────────────────────
class NewsCommands:
    @staticmethod
    def headlines(country: str = "us", limit: int = 5) -> str:
        try:
            from config_manager import config_manager
            key = config_manager.get("api_keys.newsapi")
        except Exception:
            key = None
        if not key:
            return "News API key not configured. Add it to config.json under api_keys.newsapi."
        try:
            r = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"country": country, "pageSize": limit, "apiKey": key},
                timeout=8,
            )
            r.raise_for_status()
            arts = r.json().get("articles", [])
            if not arts:
                return "No headlines found."
            lines = [f"  {i+1}. {a.get('title','')}" for i, a in enumerate(arts[:limit])]
            return "Top headlines:\n" + "\n".join(lines)
        except Exception as e:
            return f"News fetch failed: {e}"
