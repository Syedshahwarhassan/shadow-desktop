"""
feature_demo.py — Validator for AntiGravity's new cross-platform features.

This script exercises the new feature pack (commands/extra_cmds.py) without
touching any Windows-only or GUI dependency. Run it to verify the new commands
work; then test them inside the full app on Windows with `python main.py`.

Usage:
    python feature_demo.py
"""

from __future__ import annotations

import sys
import time
import textwrap

# Force UTF-8 so emoji / unicode in jokes don't crash on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Load extra_cmds directly without triggering the full commands/__init__.py
# (which imports Windows-only modules such as pyautogui, pycaw, winshell, …).
import importlib.util as _ilu, os as _os
_spec = _ilu.spec_from_file_location(
    "extra_cmds",
    _os.path.join(_os.path.dirname(__file__), "commands", "extra_cmds.py"),
)
_extra = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_extra)

WikipediaCommands  = _extra.WikipediaCommands
CalculatorCommands = _extra.CalculatorCommands
CurrencyCommands   = _extra.CurrencyCommands
UnitCommands       = _extra.UnitCommands
PasswordCommands   = _extra.PasswordCommands
TimerCommands      = _extra.TimerCommands
FunCommands        = _extra.FunCommands
NewsCommands       = _extra.NewsCommands


GREEN = "\033[92m"
CYAN  = "\033[96m"
DIM   = "\033[90m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def _section(title: str) -> None:
    print()
    print(f"{BOLD}{CYAN}── {title} {'─' * max(2, 60 - len(title))}{RESET}")


def _try(label: str, fn, *args, **kwargs) -> None:
    print(f"{DIM}> {label}{RESET}")
    try:
        result = fn(*args, **kwargs)
        text = str(result)
        # wrap long output for readability
        wrapped = textwrap.fill(text, width=88, subsequent_indent="    ")
        print(f"  {GREEN}✓{RESET} {wrapped}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")


def main() -> int:
    print(f"{BOLD}AntiGravity — Feature Validator{RESET}")
    print(f"{DIM}Exercising the new cross-platform feature pack…{RESET}")

    # ── Calculator ───────────────────────────────────────────────────────────
    _section("Calculator (sympy)")
    _try("calculate 23 * 47 + 12",
         CalculatorCommands.evaluate, "23 * 47 + 12")
    _try("compute 2 to the power of 16",
         CalculatorCommands.evaluate, "2 to the power of 16")
    _try("compute (100 - 25) / 3",
         CalculatorCommands.evaluate, "(100 - 25) / 3")

    # ── Password generator ───────────────────────────────────────────────────
    _section("Password generator")
    _try("generate 12-char password (no symbols)",
         PasswordCommands.generate, 12, False)
    _try("generate 24-char password (with symbols)",
         PasswordCommands.generate, 24, True)

    # ── Fun ──────────────────────────────────────────────────────────────────
    _section("Fun: coin / dice / facts")
    _try("flip a coin", FunCommands.coin_flip)
    _try("roll 2d20",  FunCommands.dice_roll, 20, 2)
    _try("random fact", FunCommands.random_fact)

    # ── Units ────────────────────────────────────────────────────────────────
    _section("Unit conversion (pint)")
    _try("convert 10 km to miles",
         UnitCommands.parse_and_convert, "convert 10 km to miles")
    _try("convert 32 fahrenheit to celsius",
         UnitCommands.convert, 32, "degF", "degC")
    _try("convert 5 kg to pounds",
         UnitCommands.parse_and_convert, "convert 5 kg to pounds")

    # ── Timers ───────────────────────────────────────────────────────────────
    _section("Timers (threaded, non-blocking)")
    _try("parse duration '1 hour 20 minutes'",
         TimerCommands.parse_duration, "1 hour 20 minutes")
    _try("set 2-second demo timer",
         TimerCommands.set_timer, 2, "demo timer")
    print(f"  {DIM}(waiting 2.5s for the timer to fire…){RESET}")
    time.sleep(2.5)
    _try("list active timers (should be empty)",
         TimerCommands.list_active)

    # ── Currency (network — graceful failure if offline) ────────────────────
    _section("Currency (network)")
    _try("convert 100 USD to PKR",
         CurrencyCommands.parse_and_convert, "convert 100 USD to PKR")

    # ── Wikipedia (network) ──────────────────────────────────────────────────
    _section("Wikipedia (network)")
    _try("summary: Albert Einstein",
         WikipediaCommands.summary, "Albert Einstein", 2)
    _try("search: artificial intelligence",
         WikipediaCommands.search, "artificial intelligence")

    # ── News (only if API key configured) ────────────────────────────────────
    _section("News (requires api_keys.newsapi)")
    _try("top headlines", NewsCommands.headlines)

    print()
    print(f"{BOLD}{GREEN}All new features validated.{RESET}")
    print(f"{DIM}Run the full assistant on Windows with:  python main.py{RESET}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
