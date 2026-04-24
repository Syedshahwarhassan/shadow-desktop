import re
from .system_cmds import SystemCommands
from .desktop_cmds import DesktopCommands
from .productivity_cmds import ProductivityCommands
from .web_cmds import WebCommands
from .dev_cmds import DevCommands
from .messaging import MessagingCommands
from .typing_cmds import TypingCommands, DictationMode
from .media_cmds import MediaCommands
from ai_brain import ai_brain

# ── Urdu → English keyword map ───────────────────────────────────────────────
# Handles STT variations: mazak / maza / majak / مذاق → joke
URDU_MAP = {
    # Open / Launch  (put AFTER the app name, so "spotify kholo" → "open spotify")
    "kholo":        "open",
    "kholna":       "open",
    "khol do":      "open",
    "open karo":    "open",
    "chalaao":      "open",
    "chalao":       "open",
    "launch karo":  "open",
    # Close
    "band karo":    "close",
    "band":         "close",
    # Volume
    "awaaz":        "volume",
    "awaaz barhaao":"volume up",
    "awaaz kam karo":"volume down",
    "awaaz zyada":  "volume up",
    "awaaz thodi":  "volume down",
    "volume barhaao":"volume up",
    "volume kam karo":"volume down",
    # Brightness
    "roushni":      "brightness",
    # Screenshot
    "screenshot lo":"screenshot",
    # Power
    "pc band karo":       "shutdown",
    "computer band karo": "shutdown",
    "band karo computer": "shutdown",
    "restart karo":       "restart",
    "reboot karo":        "restart",
    "lock karo":          "lock screen",
    # Search
    "search karo":  "search",
    "dhundho":      "search",
    "talash karo":  "search",
    # Play / Music
    "bajao":        "play",
    "play karo":    "play",
    "gana sunao":   "play",
    "geet sunao":   "play",
    # Scroll
    "neeche":       "scroll down",
    "upar":         "scroll up",
    "neeche jao":   "scroll down",
    "upar jao":     "scroll up",
    "neeche karo":  "scroll down",
    "upar karo":    "scroll up",
    "scroll karo":  "scroll down",
    "scrol":        "scroll",
    "skrol":        "scroll",
    "school up":    "scroll up",
    "school down":  "scroll down",
    "scall up":     "scroll up",
    "scall down":   "scroll down",
    "mausam":       "weather",
    "mausam batao": "weather in",
    # Joke — many STT variations
    "mazak":        "joke",
    "maza":         "joke",
    "majak":        "joke",
    "mazak sunao":  "joke",
    "latifa":       "joke",
    "latifa sunao": "joke",
    "funny":        "joke",
    # Note
    "note likho":   "take note",
    "note karo":    "take note",
    # Time
    "waqt":         "time",
    "waqt batao":   "what time is it",
    "time batao":   "what time is it",
    # Quote / motivation
    "aqwal":        "quote",
    "motivation":   "quote",
    # Git (common mishears)
    "gift status":  "git status",
    "gaming kids status": "git status",
    "give me a gift status": "git status",
}

# Apps that appear BEFORE "open/kholo" in Urdu speech order
# e.g.  "spotify kholo"  →  normalization yields "spotify open"
# We flip them so dispatcher can match "open spotify"
def _fix_word_order(text):
    """
    If a known app name appears before the word 'open' (reversed Urdu order),
    rewrite as  'open <app>'.
    e.g. 'spotify open' → 'open spotify'
    """
    known_apps = [
        "spotify", "youtube", "tiktok", "discord", "telegram", "whatsapp",
        "chrome", "firefox", "edge", "notepad", "calculator", "file explorer",
        "explorer", "task manager", "vscode", "vs code", "steam", "netflix",
        "instagram", "facebook", "twitter", "gmail", "github", "chatgpt",
    ]
    for app in known_apps:
        # Pattern: "<app> open" or "<app> launch" or "<app> start"
        for trigger in ["open", "launch", "start", "chalaao", "chalao"]:
            pattern = rf"\b{re.escape(app)}\s+{re.escape(trigger)}\b"
            if re.search(pattern, text):
                text = re.sub(pattern, f"open {app}", text)
    return text


class CommandDispatcher:
    def __init__(self, hud):
        self.hud = hud

    def _normalize(self, text):
        """Lower-case, translate Urdu keywords, fix word order."""
        t = text.lower().strip()
        # Apply Urdu → English map (longest match first to avoid partial replacements)
        for urdu, english in sorted(URDU_MAP.items(), key=lambda x: -len(x[0])):
            t = t.replace(urdu, english)
        # Fix reversed Urdu word order
        t = _fix_word_order(t)
        return t

    def dispatch(self, raw_text):
        text = self._normalize(raw_text)
        print(f"[DISPATCH] Normalized: '{text}'")

        # -- Dictation mode check (highest priority) --------------------------
        # If dictation is active, type everything EXCEPT the stop command
        if DictationMode.is_active():
            if any(k in text for k in ["dictation off", "dictation stop", "stop dictation",
                                        "likhna band karo", "typing off", "stop typing"]):
                return DictationMode.turn_off()
            # Type whatever was said
            return DictationMode.handle(raw_text)

        if any(k in text for k in ["test voice", "voice test", "awaz check karo"]):
            return "All systems operational. If you can hear this, my voice engine is working correctly."

        # ── System Info ───────────────────────────────────────────────────────
        if any(k in text for k in ["system info", "cpu info", "stats", "how is my pc"]):
            return SystemCommands.get_system_info()

        # ── Volume ────────────────────────────────────────────────────────────
        if any(k in text for k in ["volume", "awaaz"]):
            if any(k in text for k in ["up", "increase", "zyada", "jyada", "barhaao", "more", "tez"]):
                return SystemCommands.set_volume(10)
            if any(k in text for k in ["down", "decrease", "kam", "less", "thori"]):
                return SystemCommands.set_volume(-10)
            if "mute" in text:
                return SystemCommands.set_volume(-100)
            m = re.search(r"(\d+)", text)
            if m:
                return SystemCommands.set_volume(int(m.group(1)) - 50)

        # ── Brightness ────────────────────────────────────────────────────────
        if any(k in text for k in ["brightness", "roushni"]):
            m = re.search(r"(\d+)", text)
            return SystemCommands.set_brightness(int(m.group(1)) if m else 50)

        # ── Power / Close ─────────────────────────────────────────────────────
        if any(k in text for k in ["shutdown", "turn off", "power off", "close pc", "close computer"]):
            m = re.search(r"(\d+)\s*(second|minute|min)", text)
            t = int(m.group(1)) * (60 if "min" in m.group(2) else 1) if m else 30
            return SystemCommands.shutdown(t)
        if any(k in text for k in ["restart", "reboot"]):
            return SystemCommands.restart()
        if any(k in text for k in ["lock", "screen lock"]):
            return SystemCommands.lock_screen()
            
        # Handle 'close' or 'stop' generally
        if any(k in text for k in ["close", "stop", "band karo"]):
            return "Operations paused. Standing by."

        # ── Media & Navigation ────────────────────────────────────────────────
        if "scroll" in text:
            direction = "up" if "up" in text else "down"
            return MediaCommands.scroll(direction)

        if "youtube" in text and "play" in text:
            song = text.replace("youtube", "").replace("play", "").replace("par", "").strip()
            return MediaCommands.play_on_youtube(song)

        if "spotify" in text and "play" in text:
            song = text.replace("spotify", "").replace("play", "").replace("par", "").strip()
            return MediaCommands.play_on_spotify(song)

        # General play command (defaults to YouTube)
        if text.startswith("play") or text.endswith("bajao") or text.endswith("sunao"):
            song = text.replace("play", "").replace("bajao", "").replace("sunao", "").replace("gana", "").strip()
            if song:
                return MediaCommands.play_on_youtube(song)

        # ── Typing & Dictation ────────────────────────────────────────────────
        if any(k in text for k in ["dictation on", "start typing", "likhna shuru karo"]):
            return DictationMode.turn_on()

        if any(k in text for k in ["dictation off", "stop typing", "likhna band karo"]):
            return DictationMode.turn_off()

        if text.startswith("type"):
            to_type = text.replace("type", "", 1).replace("karo", "", 1).strip()
            if to_type:
                return TypingCommands.type_text(to_type)
            return "What should I type?"

        # -- Keyboard Keys & Shortcuts --
        if text.startswith("press"):
            key = text.replace("press", "").strip()
            return TypingCommands.press_key(key)
        
        shortcuts = ["select all", "copy", "paste", "undo", "redo", "save", "new tab"]
        for s in shortcuts:
            if s in text:
                return TypingCommands.keyboard_shortcut(s)

        # ── Open app ─────────────────────────────────────────────────────────
        # Matches: "open X", "launch X", "start X", "X open", "X chalao"
        triggers = ["open", "launch", "start", "run"]
        for trigger in triggers:
            if trigger in text:
                # Case 1: "open notepad" (Trigger first)
                if text.startswith(trigger):
                    app = text[len(trigger):].strip()
                # Case 2: "notepad open" (Trigger at the end)
                elif text.endswith(trigger):
                    app = text[:text.index(trigger)].strip()
                # Case 3: Trigger in middle
                else:
                    parts = text.split(trigger)
                    # Use the part that looks more like an app name (usually the longer one or specific one)
                    app = parts[1].strip() if parts[1].strip() else parts[0].strip()

                # Clean up noise
                app = re.sub(r"\b(please|karo|do|ab|now|ko)\b", "", app).strip()

                if not app:
                    continue # Try next trigger if this one yielded nothing

                # Special cases
                if any(k in app for k in ["download", "downloads"]):
                    return DesktopCommands.open_downloads()
                if any(k in app for k in ["file explorer", "explorer", "files", "my computer"]):
                    return SystemCommands.open_file_explorer()
                if "task manager" in app:
                    return SystemCommands.open_app("task manager")
                if any(k in app for k in ["vs code", "vscode", "visual studio code"]):
                    return DevCommands.open_vscode()

                return SystemCommands.open_app(app)

        # ── Screenshot ────────────────────────────────────────────────────────
        if "screenshot" in text:
            return DesktopCommands.screenshot()

        # ── Note ──────────────────────────────────────────────────────────────
        if "note" in text:
            note = re.sub(r"(take note|note down|note likho|note karo|note)", "", text).strip()
            if note:
                return DesktopCommands.take_note(note)
            return "What would you like to note down?"

        # ── Time ──────────────────────────────────────────────────────────────
        if any(k in text for k in ["time", "clock", "what time"]):
            import time as _t
            return f"The time is {_t.strftime('%I:%M %p')}."

        # ── Joke ──────────────────────────────────────────────────────────────
        if any(k in text for k in ["joke", "funny", "laugh", "latifa"]):
            return ProductivityCommands.tell_joke()

        # ── Weather ───────────────────────────────────────────────────────────
        if "weather" in text:
            city = text.split("in")[-1].strip() if " in " in text else "Lahore"
            return ProductivityCommands.get_weather(city)

        # ── Stock / Crypto ────────────────────────────────────────────────────
        if any(k in text for k in ["price", "stock", "share", "crypto"]):
            words = text.split()
            symbol = words[-1].upper() if words else "AAPL"
            return ProductivityCommands.stock_price(symbol)

        # ── Quote ─────────────────────────────────────────────────────────────
        if any(k in text for k in ["quote", "aqwal", "motivation"]):
            return ProductivityCommands.get_quote()

        # ── Trash ─────────────────────────────────────────────────────────────
        if any(k in text for k in ["trash", "recycle bin", "empty bin"]):
            return DesktopCommands.empty_trash()

        # ── Search ────────────────────────────────────────────────────────────
        if any(k in text for k in ["search", "find", "google"]):
            query = re.sub(r"(search for|search on google|search|find|google)", "", text).strip()
            return WebCommands.search_google(query)

        # ── Play ──────────────────────────────────────────────────────────────
        if "play" in text:
            query = re.sub(r"(play on youtube|play karo|bajao|play)", "", text).strip()
            return WebCommands.play_youtube(query)

        # ── Developer ─────────────────────────────────────────────────────────
        if any(k in text for k in ["git status", "git push", "git pull"]):
            return DevCommands.git_status()

        # ── WhatsApp Messaging ─────────────────────────────────────────────────
        # Triggers: "whatsapp", "send message", "message X", "X ko whatsapp"
        if any(k in text for k in ["whatsapp", "send message", "send whatsapp",
                                    "ko whatsapp", "ko message", "text message"]):
            contact, message = MessagingCommands.parse_whatsapp_command(raw_text)
            if contact and message:
                return MessagingCommands.send_whatsapp(contact, message)
            elif contact and not message:
                return f"What message should I send to {contact}?"
            else:
                return ("Please say: 'send WhatsApp to [name] [message]' or "
                        "'[name] ko WhatsApp karo [message]'")

        if any(k in text for k in ["list contacts", "my contacts", "contacts list",
                                    "contacts batao", "contacts dikhao"]):
            return MessagingCommands.list_contacts()

        # ── AI Fallback ───────────────────────────────────────────────────────
        print("[DISPATCH] No local match → AI fallback")
        return ai_brain.get_response(raw_text)
