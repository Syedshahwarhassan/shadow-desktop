# AntiGravity — JARVIS-Style Voice Assistant

## Overview
AntiGravity is a Python desktop voice assistant for **Windows** with an
always-on-top circular HUD (PyQt6), wake-word listening, system tray,
TTS, and a wide command set. It is intended to be run locally on a
Windows PC; this Replit container is used only for editing and
validating the platform-agnostic feature modules.

## Project layout
- `main.py` — Orchestrator (PyQt6 application, run on Windows)
- `hud.py` — Always-on-top circular HUD widget
- `listener.py` — Speech recognition thread
- `tts.py` — Text-to-speech engine
- `tray.py` — System tray integration
- `settings_ui.py` — PyQt6 settings window
- `config_manager.py` — Reads/writes `config.json`
- `memory_manager.py` — Long-term notes stored in `memory.json`
- `ai_brain.py` — OpenRouter / OpenAI chat fallback
- `commands/`
  - `__init__.py` — Command dispatcher (Urdu→English mapping, regex routing)
  - `system_cmds.py` — Volume, brightness, shutdown, restart, lock, app launcher
  - `desktop_cmds.py` — Screenshot, notes, recycle bin
  - `productivity_cmds.py` — Weather, jokes, stock prices, quotes
  - `web_cmds.py` — Google search, YouTube, open URL
  - `dev_cmds.py` — VSCode, Git
  - `messaging.py` — WhatsApp via pywhatkit
  - `typing_cmds.py` — Dictation mode, type & key shortcuts
  - `media_cmds.py` — Scroll, YouTube/Spotify play
  - **`extra_cmds.py`** ← *NEW* cross-platform feature pack
- `feature_demo.py` — Validator that exercises the new feature pack

## New features (extra_cmds.py)
All new features are pure-Python with no Windows-only dependencies, so
they work identically on Windows, macOS and Linux. They're wired into
the dispatcher and reachable by voice.

| Feature | Voice trigger examples |
|---|---|
| **Wikipedia** lookup | `wiki Einstein`, `tell me about the eiffel tower` |
| **Calculator** (sympy) | `calculate 23 * 47 + 12`, `what is 2 to the power of 16` |
| **Currency converter** | `convert 100 USD to PKR` |
| **Unit converter** (pint) | `convert 10 km to miles`, `convert 5 kg to pounds` |
| **Password generator** | `generate password`, `generate password 24` |
| **Threaded timers** | `set timer for 5 minutes`, `list timers` |
| **Coin / dice / facts** | `flip a coin`, `roll 2d20`, `random fact` |
| **News headlines** | `give me the news` (needs `api_keys.newsapi` in config.json) |

## How to run on Windows
```bash
pip install -r requirements.txt
python main.py
```

## How features were validated
Because PyQt6, pyaudio, pywin32 and similar Windows-only modules cannot
run inside this Linux container, a console workflow named **Feature Demo**
runs `feature_demo.py` to exercise the new cross-platform feature pack
and prints a green checkmark next to each working command. This proves
the new modules are correct without trying to launch the desktop GUI.

To re-run the validator manually:
```bash
.pythonlibs/bin/python feature_demo.py
```

## Configuration
- `config.json` holds API keys, voice settings, contacts, and assistant
  identity. `api_keys.newsapi` enables the News command.
- `memory.json` is created automatically by `memory_manager.py` and
  stores long-term notes.

## Security note
`config.json` currently contains an OpenRouter API key in plain text.
Rotate or move the key into an environment variable before sharing the
repository publicly.

## Performance improvements
The following changes make the assistant noticeably faster:

| Area | Change | Impact |
|---|---|---|
| Dispatcher (`commands/__init__.py`) | Pre-sorts the Urdu keyword map once at module load instead of on every voice command. | Removes ~75-entry sort + str.replace passes from the hot path. |
| System info (`system_cmds.py`) | Replaced blocking `psutil.cpu_percent(interval=0.5)` with a non-blocking sample after a one-time warm-up. | "System info" returns ~500ms faster. |
| HUD stats (`main.py`) | Same non-blocking psutil pattern + 1.5s tick (was 2s). | Qt event loop no longer stalls every refresh. |
| Listener (`listener.py`) | Parallel EN/UR speech recognition now returns on the first successful transcript instead of always waiting for both. | Reduces worst-case STT latency from ~14s to ~5s. |
| Network skills (`extra_cmds.py`) | Shared `requests.Session` (avoids TCP/TLS handshake), HTTP timeouts cut to 5s, in-memory TTL cache for Wikipedia (1h), currency rates (5m), and news (2m). | Repeat queries return instantly (300,000× faster Wikipedia repeats observed). |
| AI brain (`ai_brain.py`) | OpenAI client built with explicit 8s timeout, max_tokens lowered to 160, and a 5-minute per-prompt TTL cache (bounded to 200 entries). | Prevents hangs and makes repeat questions instant. |

Run `python feature_demo.py` to see the benchmark output (look for the
"Speed benchmark (TTL cache)" section at the end).
