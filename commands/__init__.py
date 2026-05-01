"""
commands/__init__.py  --  Shadow Assistant NL-First Command Dispatcher
"""

import sys
import json
import time
import httpx
from dataclasses import dataclass, field
from typing import Optional, Callable

# Force UTF-8 output so Unicode in print() never crashes on Windows cp1252 terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .system_cmds       import SystemCommands
from .desktop_cmds      import DesktopCommands
from .productivity_cmds import ProductivityCommands
from .web_cmds          import WebCommands
from .dev_cmds          import DevCommands
from .messaging         import MessagingCommands
from .typing_cmds       import TypingCommands, DictationMode
from .media_cmds        import MediaCommands
from .extra_cmds        import (
    WikipediaCommands, CalculatorCommands, CurrencyCommands,
    UnitCommands, PasswordCommands, TimerCommands, FunCommands, NewsCommands,
)
from .advanced_cmds     import AdvancedCommands
from ai_brain           import ai_brain
from response_tags      import ensure_action_tag
from tts                import get_tts_engine
from config_manager     import config_manager

# ── OpenRouter config (key pulled from config.json) ───────────────────────────
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Multi-model fallback rotation — verified live free models on OpenRouter
_MODELS = [
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]

_INTENT_PROMPT = """You are the intent router for Shadow, an AI desktop assistant.
Given a voice command (possibly English, Urdu, or mixed), return ONLY valid JSON — no markdown.

INTENT TABLE (intent → key params):
open_app(app_name), close_app(app_name), open_file(file_name), open_folder(folder_name),
create_file(file_name), create_folder(folder_name),
set_volume(level: 0-100|"up"|"down"|"mute"), set_brightness(level: 0-100),
screenshot, shutdown(delay_seconds=30), restart, lock_screen,
restart_shadow, close_shadow, mute_shadow, unmute_shadow, hide_shadow, show_shadow,
open_settings, system_info, system_health, get_ip, speed_test,
scroll(direction,amount), mouse_move(direction,amount), mouse_click(type:"single"|"double"),
check_port(port_number),
play_youtube(query), play_spotify(query), play_media(query),
dictation_on, dictation_off, type_text(text), press_key(key), keyboard_shortcut(shortcut),
web_search(query), wikipedia(query), weather(city="Lahore"), stock_price(symbol),
news(topic), get_quote(type), tell_joke, what_time,
translate(text,target_language), calculate(expression),
convert_unit(expression), convert_currency(expression),
generate_password(length=16), set_timer(duration_seconds,label),
set_reminder(duration_seconds,label), list_timers, cancel_reminder(target),
coin_flip, dice_roll(sides=6,count=1), random_fact,
send_whatsapp(contact,message), list_contacts, send_email(recipient,subject,body),
analyze_screen(prompt), research(topic),
add_todo(task), list_todos, complete_todo(task_id), clear_todos, pomodoro,
clipboard_get, clipboard_set(text),
window_maximize, window_minimize, window_minimize_all, window_close,
take_note(text), organize_desktop, organize_downloads, organize_documents,
clean_temp, empty_trash, set_app_volume(app_name,level),
git_status, create_project(framework,project_name),
scaffold_code(description), create_login_page(description),
test_voice, stop,
ai_chat(query)  ← ONLY if nothing else fits

URDU NOTES: kholo/chalao→open_app, band karo→close_app, awaaz barhaao→set_volume up,
bajao/sunao→play_media, mausam→weather, waqt batao→what_time,
timer lagao→set_timer, yad dilao→set_reminder, mazak/latifa→tell_joke,
likhna shuru karo→dictation_on, dhundho→web_search.

MULTI-COMMAND: If input has sequential commands, return a JSON array.

Single: {"intent":"open_app","params":{"app_name":"chrome"},"confidence":0.97}
Multi:  [{"intent":"open_app","params":{"app_name":"chrome"}},{"intent":"web_search","params":{"query":"python"}}]

Set missing params to null. Output raw JSON only."""


@dataclass
class Intent:
    intent:     str
    params:     dict          = field(default_factory=dict)
    confidence: float         = 1.0
    error:      Optional[str] = None


def classify_intent(user_text: str) -> list[Intent]:
    api_key = config_manager.get("api_keys.openrouter", "")
    if not api_key:
        return [Intent(intent="ai_chat", params={"query": user_text},
                       error="No OpenRouter API key configured.")]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://shadow-assistant",
        "X-Title": "Shadow Assistant",
    }
    # Merge system prompt into user message (Gemma models reject system role)
    merged_user = f"{_INTENT_PROMPT}\n\nVoice command: {user_text.strip()}"
    payload = {
        "messages": [
            {"role": "user", "content": merged_user},
        ],
        "temperature": 0.1,
        "max_tokens":  300,
    }

    last_err = None
    for model in _MODELS:
        try:
            resp = httpx.post(
                _OPENROUTER_URL,
                headers=headers,
                json={**payload, "model": model},
                timeout=8.0,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences some models wrap around JSON
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            print(f"[INTENT] model={model} -> {[d.get('intent') for d in data]}")
            return [
                Intent(
                    intent     = d.get("intent", "ai_chat"),
                    params     = {k: v for k, v in (d.get("params") or {}).items() if v is not None},
                    confidence = float(d.get("confidence", 1.0)),
                )
                for d in data
            ]
        except Exception as e:
            last_err = e
            print(f"[INTENT] {model} failed: {e} -- trying next model")
            continue

    return [Intent(intent="ai_chat", params={"query": user_text}, error=str(last_err))]


# ── Command Dispatcher ────────────────────────────────────────────────────────

class CommandDispatcher:
    def __init__(self, hud):
        self.hud  = hud
        self._map: dict[str, Callable] = {}
        self._register_all()

    def _reg(self, *names):
        def decorator(fn):
            for n in names:
                self._map[n] = fn
            return fn
        return decorator

    # ── Entry point ───────────────────────────────────────────────────────────

    def dispatch(self, raw_text: str):
        if DictationMode.is_active():
            stop_words = ["dictation off", "dictation stop", "stop dictation",
                          "likhna band karo", "typing off", "stop typing"]
            if any(k in raw_text.lower() for k in stop_words):
                return ensure_action_tag(DictationMode.turn_off(), default="ACTION")
            return ensure_action_tag(DictationMode.handle(raw_text), default="ACTION")

        intents = classify_intent(raw_text)

        if len(intents) == 1:
            return self._execute(intents[0], raw_text)

        def _multi():
            for intent in intents:
                result = self._execute(intent, raw_text)
                if hasattr(result, "__iter__") and not isinstance(result, str):
                    yield from result
                else:
                    yield result
        return _multi()

    def _execute(self, intent: Intent, raw_text: str):
        handler = self._map.get(intent.intent)
        if handler:
            print(f"[DISPATCH] intent={intent.intent!r} params={intent.params} conf={intent.confidence:.2f}")
            try:
                return handler(intent.params)
            except Exception as e:
                return f"[WARN] Error executing {intent.intent!r}: {e}"
        print(f"[DISPATCH] No handler for '{intent.intent}' → AI fallback")
        return ai_brain.get_response(raw_text, stream=True)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _register_all(self):

        # Meta
        @self._reg("test_voice")
        def _(p): return "[INFO] تمام سسٹم کام کر رہے ہیں۔"

        @self._reg("mute_shadow")
        def _(p):
            get_tts_engine().set_muted(True)
            return "[ACTION] آواز بند کر دی گئی ہے۔"

        @self._reg("unmute_shadow")
        def _(p):
            get_tts_engine().set_muted(False)
            return "[ACTION] آواز کھول دی گئی ہے۔"

        @self._reg("hide_shadow")
        def _(p):
            self.hud.hide_hud()
            return "[ACTION] ایچ یو ڈی چھپا دیا گیا ہے۔"

        @self._reg("show_shadow")
        def _(p):
            self.hud.show_hud()
            return "[ACTION] ایچ یو ڈی دکھا دیا گیا ہے۔"

        @self._reg("open_settings")
        def _(p):
            if hasattr(self.hud, "_settings_callback"):
                self.hud._settings_callback()
            return "[ACTION] سیٹنگز کھول رہا ہوں۔"

        @self._reg("restart_shadow")
        def _(p):
            SystemCommands.restart_self()
            return "[ACTION] دوبارہ شروع کر رہا ہوں۔"

        @self._reg("close_shadow")
        def _(p):
            SystemCommands.close_self()
            return "[ACTION] بند کر رہا ہوں۔"

        @self._reg("stop")
        def _(p): return "[ACTION] رک گیا۔"

        # System
        @self._reg("system_info")
        def _(p): return f"[INFO] {SystemCommands.get_system_info()}"

        @self._reg("system_health")
        def _(p): return f"[INFO] {AdvancedCommands.get_system_health()}"

        @self._reg("get_ip")
        def _(p): return f"[INFO] {AdvancedCommands.get_ip_info()}"

        @self._reg("speed_test")
        def _(p): return f"[INFO] {AdvancedCommands.run_speed_test()}"

        @self._reg("set_volume")
        def _(p):
            level = p.get("level", 50)
            if level == "up":     delta = 10
            elif level == "down": delta = -10
            elif level == "mute": delta = -100
            else:
                try:    delta = int(level) - 50
                except: delta = 0
            return f"[ACTION] {SystemCommands.set_volume(delta)}"

        @self._reg("set_brightness")
        def _(p):
            return f"[ACTION] {SystemCommands.set_brightness(int(p.get('level', 50)))}"

        @self._reg("screenshot")
        def _(p): return f"[ACTION] {DesktopCommands.screenshot()}"

        @self._reg("shutdown")
        def _(p):
            return f"[ACTION] {SystemCommands.shutdown(int(p.get('delay_seconds', 30)))}"

        @self._reg("restart")
        def _(p): return f"[ACTION] {SystemCommands.restart()}"

        @self._reg("lock_screen")
        def _(p): return f"[ACTION] {SystemCommands.lock_screen()}"

        @self._reg("check_port")
        def _(p): return AdvancedCommands.check_port(p.get("port_number"))

        # Apps & Files
        @self._reg("open_app")
        def _(p):
            app = p.get("app_name", "")
            if any(k in app for k in ["download", "downloads"]):
                return f"[ACTION] {DesktopCommands.open_downloads()}"
            if any(k in app for k in ["file explorer", "explorer", "files", "my computer"]):
                return f"[ACTION] {SystemCommands.open_file_explorer()}"
            if "task manager" in app:
                return f"[ACTION] {SystemCommands.open_app('task manager')}"
            if any(k in app for k in ["vs code", "vscode", "visual studio code"]):
                return ensure_action_tag(DevCommands.open_vscode(), default="ACTION")
            return f"[ACTION] {SystemCommands.open_app(app)}"

        @self._reg("close_app", "close_specific_app")
        def _(p):
            return f"[ACTION] {AdvancedCommands.close_app(p.get('app_name', ''))}"

        @self._reg("open_file")
        def _(p):
            return ensure_action_tag(
                AdvancedCommands.search_and_open_file(p.get("file_name", "")), default="ACTION")

        @self._reg("open_folder")
        def _(p):
            return ensure_action_tag(
                SystemCommands.search_and_open_folder(p.get("folder_name", "")), default="ACTION")

        @self._reg("create_file")
        def _(p): return f"[ACTION] {DesktopCommands.create_file(p.get('file_name', 'New File'))}"

        @self._reg("create_folder")
        def _(p): return f"[ACTION] {DesktopCommands.create_folder(p.get('folder_name', 'New Folder'))}"

        # Media
        @self._reg("play_youtube", "play_media")
        def _(p): return ensure_action_tag(MediaCommands.play_on_youtube(p.get("query", "")), default="ACTION")

        @self._reg("play_spotify")
        def _(p): return ensure_action_tag(MediaCommands.play_on_spotify(p.get("query", "")), default="ACTION")

        @self._reg("scroll")
        def _(p): return f"[ACTION] {MediaCommands.scroll(p.get('direction', 'down'))}"

        # Typing & Keyboard
        @self._reg("dictation_on")
        def _(p): return ensure_action_tag(DictationMode.turn_on(), default="ACTION")

        @self._reg("dictation_off")
        def _(p): return ensure_action_tag(DictationMode.turn_off(), default="ACTION")

        @self._reg("type_text")
        def _(p): return ensure_action_tag(TypingCommands.type_text(p.get("text", "")), default="ACTION")

        @self._reg("press_key")
        def _(p): return ensure_action_tag(TypingCommands.press_key(p.get("key", "")), default="ACTION")

        @self._reg("keyboard_shortcut")
        def _(p): return ensure_action_tag(TypingCommands.keyboard_shortcut(p.get("shortcut", "")), default="ACTION")

        # Mouse
        @self._reg("mouse_move")
        def _(p):
            return f"[ACTION] {AdvancedCommands.mouse_control(p.get('direction', 'down'), p.get('amount', 100))}"

        @self._reg("mouse_click")
        def _(p):
            ct = "double click" if p.get("type") == "double" else "click"
            return f"[ACTION] {AdvancedCommands.mouse_control(ct)}"

        # Web & Info
        @self._reg("web_search")
        def _(p): return ensure_action_tag(WebCommands.search_google(p.get("query", "")), default="ACTION")

        @self._reg("wikipedia")
        def _(p): return f"[INFO] {WikipediaCommands.summary(p.get('query', ''))}"

        @self._reg("weather")
        def _(p): return f"[INFO] {ProductivityCommands.get_weather(p.get('city', 'Lahore'))}"

        @self._reg("stock_price")
        def _(p): return f"[INFO] {ProductivityCommands.stock_price(p.get('symbol', 'AAPL').upper())}"

        @self._reg("news")
        def _(p): return f"[INFO] {NewsCommands.headlines()}"

        @self._reg("get_quote")
        def _(p):
            if p.get("type") == "motivational":
                return f"[INFO] {AdvancedCommands.get_motivation()}"
            return f"[INFO] {ProductivityCommands.get_quote()}"

        @self._reg("tell_joke")
        def _(p): return f"[INFO] {ProductivityCommands.tell_joke()}"

        @self._reg("what_time")
        def _(p):
            import time as _t
            return f"[INFO] ابھی {_t.strftime('%I:%M %p')} بج رہے ہیں۔"

        @self._reg("translate")
        def _(p):
            target = 'ur' if 'urdu' in p.get('target_language', '').lower() else 'en'
            return f"[INFO] {AdvancedCommands.translate_text(p.get('text', ''), target)}"

        @self._reg("calculate")
        def _(p): return f"[INFO] {CalculatorCommands.evaluate(p.get('expression', ''))}"

        @self._reg("convert_unit")
        def _(p): return f"[INFO] {UnitCommands.parse_and_convert(p.get('expression', ''))}"

        @self._reg("convert_currency")
        def _(p): return f"[INFO] {CurrencyCommands.parse_and_convert(p.get('expression', ''))}"

        @self._reg("generate_password")
        def _(p): return f"[INFO] {PasswordCommands.generate(int(p.get('length', 16)))}"

        # Timers & Reminders
        @self._reg("set_timer", "set_reminder")
        def _(p):
            secs  = int(p.get("duration_seconds", 0))
            label = p.get("label", "reminder")
            if not secs:
                return "[WARN] How long should the timer run? (e.g. '5 minutes')"
            def _on_fire(msg):
                if hasattr(self.hud, "reminder_signal"):
                    self.hud.reminder_signal.emit(label)
                get_tts_engine().speak(f"[EXCITED] {msg}")
            return TimerCommands.set_timer(secs, label, on_fire=_on_fire)

        @self._reg("list_timers")
        def _(p): return f"[INFO] {TimerCommands.list_active()}"

        @self._reg("cancel_reminder")
        def _(p):
            from datetime import datetime
            target = str(p.get("target", ""))
            if not target:
                return "[WARN] Which reminder should I cancel?"
            try:
                idx    = int(target) - 1
                timers = [t for t in TimerCommands._timers if t["fires_at"] > datetime.now()]
                if 0 <= idx < len(timers):
                    label = timers[idx]["label"]
                    timers[idx]["timer"].cancel()
                    TimerCommands._timers.remove(timers[idx])
                    TimerCommands._save_reminders()
                    self.hud.refresh_reminders()
                    return f"[ACTION] Cancelled reminder '{label}'."
            except (ValueError, TypeError):
                pass
            for t in TimerCommands._timers:
                if target.lower() in t["label"].lower():
                    t["timer"].cancel()
                    TimerCommands._timers.remove(t)
                    TimerCommands._save_reminders()
                    self.hud.refresh_reminders()
                    return f"[ACTION] Cancelled reminder '{t['label']}'."
            return f"[WARN] No active reminder matching '{target}'."

        # Fun
        @self._reg("coin_flip")
        def _(p): return f"[INFO] {FunCommands.coin_flip()}"

        @self._reg("dice_roll")
        def _(p): return f"[INFO] {FunCommands.dice_roll(int(p.get('sides', 6)), int(p.get('count', 1)))}"

        @self._reg("random_fact")
        def _(p): return f"[INFO] {FunCommands.random_fact()}"

        # Messaging
        @self._reg("send_whatsapp")
        def _(p):
            contact, message = p.get("contact", ""), p.get("message", "")
            if contact and message:
                return ensure_action_tag(MessagingCommands.send_whatsapp(contact, message), default="ACTION")
            elif contact:
                return f"[WARN] What's the message for {contact}?"
            return "[WARN] Say: 'WhatsApp [name] [message]'."

        @self._reg("list_contacts")
        def _(p): return ensure_action_tag(MessagingCommands.list_contacts(), default="INFO")

        @self._reg("send_email")
        def _(p):
            return AdvancedCommands.send_email(
                p.get("recipient", ""), p.get("subject", ""), p.get("body", ""))

        # AI Vision & Research
        @self._reg("analyze_screen")
        def _(p):
            prompt = p.get("prompt", "Describe what is on this screen.")
            return ensure_action_tag(AdvancedCommands.analyze_screen(prompt), default="INFO")

        @self._reg("research")
        def _(p):
            topic = p.get("topic", "")
            if not topic:
                return "[WARN] Which topic should I research?"
            return ensure_action_tag(AdvancedCommands.autonomous_research(topic), default="INFO")

        # Productivity / Todos
        @self._reg("add_todo")
        def _(p): return f"[ACTION] {AdvancedCommands.todo_manager('add', p.get('task', ''))}"

        @self._reg("list_todos")
        def _(p): return f"[INFO] {AdvancedCommands.todo_manager('list')}"

        @self._reg("complete_todo")
        def _(p): return f"[ACTION] {AdvancedCommands.todo_manager('done', p.get('task_id'))}"

        @self._reg("clear_todos")
        def _(p): return f"[ACTION] {AdvancedCommands.todo_manager('clear')}"

        @self._reg("pomodoro")
        def _(p):
            resp = AdvancedCommands.start_pomodoro()
            TimerCommands.set_timer(25 * 60, "Pomodoro Break",
                                    on_fire=lambda msg: print(f"[POMODORO] {msg}"))
            return ensure_action_tag(resp, default="REMIND")

        @self._reg("clipboard_get")
        def _(p): return f"[INFO] {AdvancedCommands.clipboard_action('get')}"

        @self._reg("clipboard_set")
        def _(p): return f"[ACTION] {AdvancedCommands.clipboard_action('set', p.get('text', ''))}"

        @self._reg("take_note")
        def _(p):
            text = p.get("text", "")
            if not text:
                return "[WARN] What should I write in the note?"
            return f"[ACTION] {DesktopCommands.take_note(text)}"

        # Window Management
        @self._reg("window_maximize")
        def _(p): return AdvancedCommands.window_control("maximize")

        @self._reg("window_minimize")
        def _(p): return AdvancedCommands.window_control("minimize")

        @self._reg("window_minimize_all")
        def _(p): return AdvancedCommands.window_control("minimize_all")

        @self._reg("window_close")
        def _(p): return AdvancedCommands.window_control("close")

        # Desktop Cleaning
        @self._reg("organize_desktop")
        def _(p):
            import winshell
            return AdvancedCommands.organize_folder(winshell.desktop())

        @self._reg("organize_downloads")
        def _(p):
            import winshell
            return AdvancedCommands.organize_folder(winshell.folder("downloads"))

        @self._reg("organize_documents")
        def _(p):
            import winshell
            return AdvancedCommands.organize_folder(winshell.folder("personal"))

        @self._reg("clean_temp")
        def _(p): return AdvancedCommands.clean_temp_files()

        @self._reg("empty_trash")
        def _(p): return f"[ACTION] {DesktopCommands.empty_trash()}"

        @self._reg("set_app_volume")
        def _(p):
            return AdvancedCommands.set_app_volume(
                p.get("app_name", ""), int(p.get("level", 50)) / 100.0)

        # Dev Tools
        @self._reg("git_status")
        def _(p): return ensure_action_tag(DevCommands.git_status(), default="INFO")

        @self._reg("create_project")
        def _(p):
            return DevCommands.create_project_starter(
                p.get("framework", "react"), p.get("project_name", "my-project"))

        @self._reg("scaffold_code")
        def _(p): return DevCommands.scaffold_project(p.get("description", ""))

        @self._reg("create_login_page")
        def _(p): return DevCommands.create_login_page(p.get("description", ""))

        # AI Chat fallback
        @self._reg("ai_chat")
        def _(p):
            print("[DISPATCH] Routing to AI brain.")
            return ai_brain.get_response(p.get("query", ""), stream=True)
