import re
from .system_cmds import SystemCommands
from .desktop_cmds import DesktopCommands
from .productivity_cmds import ProductivityCommands
from .web_cmds import WebCommands
from .dev_cmds import DevCommands
from .messaging import MessagingCommands
from .typing_cmds import TypingCommands, DictationMode
from .media_cmds import MediaCommands
from .extra_cmds import (
    WikipediaCommands,
    CalculatorCommands,
    CurrencyCommands,
    UnitCommands,
    PasswordCommands,
    TimerCommands,
    FunCommands,
    NewsCommands,
)
from .advanced_cmds import AdvancedCommands
from ai_brain import ai_brain

# ── Urdu → English keyword map ───────────────────────────────────────────────
# Handles STT variations: mazak / maza / majak / مذاق → joke
URDU_MAP = {
    # Open / Launch
    "kholo":        "open",
    "kholna":       "open",
    "khol do":      "open",
    "open karo":    "open",
    "chalaao":      "open",
    "chalao":       "open",
    "launch karo":  "open",
    "kho":          "open",
    "کھولو":         "open",
    "چلاؤ":          "open",
    "کھول دو":       "open",
    "کھو":           "open",
    # Close
    "band karo":    "close",
    "band":         "close",
    "shut off":     "close",
    "turn off":     "close",
    "بند کرو":       "close",
    "بند":          "close",
    "khamosh":      "mute",
    "chup":         "mute",
    "gayab":        "hide",
    "chhup":        "hide",
    "dikhao":       "show",
    "khamosh ho jao": "mute yourself",
    "chup ho jao":   "mute yourself",
    "gayab ho jao":  "hide yourself",
    "chhup jao":     "hide yourself",
    "samne ao":      "show yourself",
    # Volume
    "awaaz":        "volume",
    "awaaz barhaao":"volume up",
    "awaaz barhao":  "volume up",
    "awaaz kam karo":"volume down",
    "awaaz zyada":  "volume up",
    "awaaz jyada":  "volume up",
    "awaaz thodi":  "volume down",
    "awaaz kam":    "volume down",
    "volume barhaao":"volume up",
    "volume barhao": "volume up",
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
    "suna do":      "play",
    "sunao":        "play",
    "bajao":        "play",
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
    "note banao":   "take note",
    "نوٹ لکھو":      "take note",
    # Time
    "waqt":         "time",
    "waqt batao":   "what time is it",
    "time batao":   "what time is it",
    "وقت بتاؤ":      "what time is it",
    "کیا ٹائم":      "what time is it",
    "ٹائم بتاؤ":      "what time is it",
    "ٹائم کیا ہوا":    "what time is it",
    "time kya hai": "what time is it",
    "mujhe time batao": "what time is it",
    "mujhe waqt batao": "what time is it",
    "مجھے ٹائم بتاؤ":    "what time is it",
    "مجھے وقت بتاؤ":    "what time is it",
    # Quote / motivation
    "aqwal":        "quote",
    "motivation":   "quote",
    "اقوال":         "quote",
    # Timer / Alarm
    "timer lagao":  "set timer",
    "timer set karo": "set timer",
    "timer laga do": "set timer",
    "ka timer":     "set timer",
    "alarm lagao":  "set alarm",
    "alarm set karo": "set alarm",
    "alarm laga do": "set alarm",
    "ka alarm":     "set alarm",
    "baje":         "pm",
    "yad dilana":   "remind me",
    "yad dilao":    "remind me",
    "یاد دلانا":      "remind me",
    "یاد دلاؤ":       "remind me",
    "ریمائنڈ می":     "remind me",
    "ٹائمر لگاؤ":      "set timer",
    "الارم لگاؤ":      "set alarm",
    # Dictation/Typing
    "likhna shuru karo": "dictation on",
    "لکھنا شروع کرو":    "dictation on",
    "likhna band karo":  "dictation off",
    "لکھنا بند کرو":     "dictation off",
    "ٹائپ کرو":          "type",
    # WhatsApp
    "whatsapp":   "whatsapp",
    "میسج بھیجو":    "message bhejo",
    # Advanced
    "ip batao":     "my ip",
    "speed test":   "speed test",
    "safai karo":   "organize desktop",
    "صفائی کرو":      "organize desktop",
    "صاف کرو":       "organize desktop",
    "desktop saaf karo": "organize desktop",
    "downloads saaf karo": "organize downloads",
    "documents saaf karo": "organize documents",
    "bin khali karo": "empty trash",
    "kuda saaf karo": "empty trash",
    "faltu files khatam karo": "clean temp",
    "temp saaf karo": "clean temp",
    "urdu mein":    "translate to urdu",
    "english mein": "translate to english",
    "health check": "system health",
    # Productivity
    "kaam likho":   "add to do",
    "task likho":   "add to do",
    "tasks dikhao": "list to do",
    "kaam ho gaya": "task done",
    "clipboard check": "get clipboard",
    "copy karo":    "set clipboard",
    "focus mode":   "pomodoro",
    "bara karo":    "maximize window",
    "chota karo":   "minimize window",
    "screen saaf karo": "minimize all",
    "file kholo":   "open file",
    # Out of Minds
    "screen dekho": "analyze screen",
    "ye kya hai":   "analyze screen",
    "research karo": "research topic",
    "mouse upar":   "mouse up",
    "mouse neeche": "mouse down",
    "mouse dayein": "mouse right",
    "mouse bayein": "mouse left",
    "click karo":   "mouse click",
    # Git (common mishears)
    "gift status":  "git status",
    "gaming kids status": "git status",
    "give me a gift status": "git status",
    # Conjunctions
    "aur":        "and",
    "phir":       "then",
    "phr":        "then",
    "uske baad":  "then",
    "اور":         "and",
    "پھر":         "then",
    # Time units for reminders
    "minute":     "minute",
    "minutes":    "minutes",
    "ghante":     "hours",
    "ghanta":     "hour",
    "second":     "second",
    "seconds":    "seconds",
    "minat":      "minute",
    "min":        "minute",
    "منٹ":        "minute",
    "منٹس":       "minutes",
    "گھنٹہ":       "hour",
    "گھنٹے":       "hours",
    "سیکنڈ":       "second",
    "mein":       "in",
    "main":       "in",
    "ان":         "in",
    "ko":         "to",
    "ٹو":         "to",
    "aadha":      "30 minute",
    "aadha ghanta":"30 minute",
    "dedh ghanta":"90 minute",
    "dhai ghante": "150 minute",
    "sawa ghanta": "75 minute",
    "paun ghanta": "45 minute",
    "aadhe":      "half",
    "aadha":      "half",
    "آدھا":        "half",
    "ڈیڑھ":        "1.5",
    "ڈھائی":        "2.5",
    "سوا":         "1.15",
    "پونے":        "0.75",
}

# Pre-sort the Urdu map ONCE at module load (longest-key first) so the
# dispatcher doesn't pay the O(n log n) sort cost on every voice command.
_URDU_SORTED = sorted(URDU_MAP.items(), key=lambda x: -len(x[0]))

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
        "settings", "setting",
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
        # Apply pre-sorted Urdu → English map
        for urdu, english in _URDU_SORTED:
            if urdu in t:
                if len(urdu) <= 3:
                    t = re.sub(rf"\b{re.escape(urdu)}\b", english, t)
                else:
                    t = t.replace(urdu, english)
        # Fix reversed Urdu word order
        t = _fix_word_order(t)
        return t

    def _split_commands(self, text):
        """
        Splits a single string into multiple potential commands based on conjunctions.
        Uses heuristics to distinguish between compound queries (cats and dogs)
        and compound intents (search cats and open chrome).
        """
        t = text.lower().strip()
        
        # 1. Universal strong splitters (always split)
        strong_splitters = r"\b(?:then|phir|uske baad|followed by|next|پھر)\b"
        if re.search(strong_splitters, t):
            parts = re.split(strong_splitters, t, flags=re.IGNORECASE)
            return [p.strip() for p in parts if p.strip()]

        # 2. Conditional splitters (and/aur/اور)
        # We only split by 'and' if the second part starts with a known command verb.
        weak_splitters = r"\b(?:and|aur|اور)\b"
        if re.search(weak_splitters, t):
            parts = re.split(weak_splitters, t, flags=re.IGNORECASE)
            if len(parts) > 1:
                # Verbs/Keywords that indicate a NEW command intent
                action_verbs = {
                    "open", "opening", "kholo", "launch", "start", "run", "chalao", "kho",
                    "close", "closing", "band", "exit", "quit",
                    "create", "make", "banao", "likho", "take",
                    "search", "searching", "find", "google", "dhundho", "talash",
                    "play", "playing", "bajao", "sunao", "gana",
                    "volume", "brightness", "awaaz", "mute",
                    "screenshot", "capture",
                    "shutdown", "restart", "reboot", "lock",
                    "type", "typing", "press", "click", "mouse", "scroll",
                    "weather", "mausam", "time", "waqt", "quote", "joke", "latifa", "news",
                    "timer", "alarm", "remind", "yad", "reminder",
                    "translate", "ip", "speed", "safai", "clean", "empty",
                }
                
                final_commands = [parts[0].strip()]
                for p in parts[1:]:
                    p_clean = p.strip()
                    # Check if the first word of this part is a known action verb
                    first_word = p_clean.split()[0] if p_clean else ""
                    if first_word in action_verbs:
                        final_commands.append(p_clean)
                    else:
                        # Not an action? Merge it back to the previous command (e.g. "cats and dogs")
                        # We use the original conjunction "and" for the dispatcher's sake
                        final_commands[-1] = f"{final_commands[-1]} and {p_clean}"
                
                return [c.strip() for c in final_commands if c.strip()]

        return [text.strip()]

    def dispatch(self, raw_text):
        """
        Main entry point. Handles splitting and sequential execution.
        """
        # 1. Quick normalization for splitting check
        normalized_check = self._normalize(raw_text)
        
        # 2. Split into parts
        commands = self._split_commands(raw_text)
        
        if len(commands) > 1:
            print(f"[DISPATCH] Multi-command detected: {commands}")
            
            def _multi_generator():
                for i, cmd in enumerate(commands):
                    # For each sub-command, call the internal executor
                    resp = self._execute_single(cmd)
                    
                    # If it's a generator (AI streaming), yield from it
                    if hasattr(resp, "__iter__") and not isinstance(resp, str):
                        for chunk in resp:
                            yield chunk
                    else:
                        # If it's a string, yield it as a single "sentence"
                        yield resp
                    
                    # Add a small separator or pause indicator if needed
                    # but usually sequential yielding is enough for TTS
                
            return _multi_generator()
        else:
            return self._execute_single(raw_text)

    def _execute_single(self, raw_text):
        text = self._normalize(raw_text)
        print(f"[DISPATCH] Processing: '{text}'")

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

        if any(k in text for k in ["system health", "health check", "battery status"]):
            return AdvancedCommands.get_system_health()

        # ── Network ───────────────────────────────────────────────────────────
        if any(k in text for k in ["my ip", "ip address", "ip batao"]):
            return AdvancedCommands.get_ip_info()

        if any(k in text for k in ["speed test", "internet speed"]):
            return AdvancedCommands.run_speed_test()

        # ── AI Vision (Out of Minds) ──────────────────────────────────────────
        if any(k in text for k in ["analyze screen", "screen dekho", "ye kya hai"]):
            prompt = re.sub(r"(analyze screen|screen dekho|ye kya hai|batao|karo|shadow|ye)", "", text).strip()
            if not prompt: prompt = "Describe what is on this screen."
            return AdvancedCommands.analyze_screen(prompt)

        # ── Autonomous Research ───────────────────────────────────────────────
        if "research" in text:
            topic = re.sub(r"(research topic|research karo|research on|research)", "", text).strip()
            if topic:
                return AdvancedCommands.autonomous_research(topic)
            return "Kis topic par research karun?"

        # ── Mouse Control ─────────────────────────────────────────────────────
        if "mouse" in text or "click" in text:
            amount_match = re.search(r"(\d+)", text)
            amount = amount_match.group(1) if amount_match else 100
            
            if "upar" in text or "up" in text: return AdvancedCommands.mouse_control("up", amount)
            if "neeche" in text or "down" in text: return AdvancedCommands.mouse_control("down", amount)
            if "dayein" in text or "right" in text: return AdvancedCommands.mouse_control("right", amount)
            if "bayein" in text or "left" in text: return AdvancedCommands.mouse_control("left", amount)
            if "double click" in text: return AdvancedCommands.mouse_control("double click")
            if "click" in text: return AdvancedCommands.mouse_control("click")

        # ── Port Checker ──────────────────────────────────────────────────────
        if re.search(r"\bport\b", text):
            m = re.search(r"(\d+)", text)
            if m:
                return AdvancedCommands.check_port(m.group(1))

        # ── Volume & Mute ─────────────────────────────────────────────────────
        if any(k in text for k in ["volume", "awaaz", "mute"]):
            if any(k in text for k in ["up", "increase", "zyada", "jyada", "barhaao", "more", "tez"]):
                return SystemCommands.set_volume(10)
            if any(k in text for k in ["down", "decrease", "kam", "less", "thori"]):
                return SystemCommands.set_volume(-10)
            if "mute" in text:
                return SystemCommands.set_volume(-100)
            m = re.search(r"(\d+)", text)
            if m:
                return SystemCommands.set_volume(int(m.group(1)) - 50)

        # ── Mute / Unmute Shadow ──────────────────────────────────────────────
        if any(k in text for k in ["mute yourself", "mute shadow", "silent shadow", "stop talking"]):
            from tts import tts_engine
            tts_engine.set_muted(True)
            return "Zaroor, main khamosh ho jati hoon. Jab bhi baat karni ho, 'unmute' kahein."

        if any(k in text for k in ["unmute yourself", "unmute shadow", "speak shadow"]):
            from tts import tts_engine
            tts_engine.set_muted(False)
            return "Theek hai, main ab bol sakti hoon."

        # ── Hide / Show Shadow ────────────────────────────────────────────────
        if any(k in text for k in ["hide yourself", "hide shadow", "hide it", "go away"]):
            self.hud.hide_hud()
            return "Theek hai, main chhup jati hoon. Aap mujhe hotkey se ya 'show shadow' keh kar wapas bula sakte hain."

        if any(k in text for k in ["show yourself", "show shadow", "show it", "come back"]):
            self.hud.show_hud()
            return "Main wapas aa gayi hoon."

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
            
        # ── Self Power / Close ────────────────────────────────────────────────
        if any(k in text for k in ["restart yourself", "restart shadow", "restart system"]):
            return SystemCommands.restart_self()
        if any(k in text for k in ["close yourself", "close shadow", "exit yourself", "quit yourself"]):
            return SystemCommands.close_self()

        # ── Settings ──────────────────────────────────────────────────────────
        if any(k in text for k in ["open settings", "open setting", "show settings", "show setting", "settings open", "setting open"]):
            if hasattr(self.hud, "_settings_callback"):
                self.hud._settings_callback()
            return "Zaroor, settings open kar di hain."

        # ── Media & Navigation ────────────────────────────────────────────────
        if "scroll" in text:
            direction = "up" if "up" in text else "down"
            return MediaCommands.scroll(direction)

        if "youtube" in text and "play" in text:
            song = re.sub(r"\b(youtube|play|pe|par|on)\b", "", text).strip()
            return MediaCommands.play_on_youtube(song)

        if "spotify" in text and "play" in text:
            song = re.sub(r"\b(spotify|play|pe|par|on)\b", "", text).strip()
            return MediaCommands.play_on_spotify(song)

        # General play command (defaults to YouTube for reliable auto-play)
        if "play" in text or "gana" in text or "music" in text:
            # Use regex to remove keywords with word boundaries
            song = re.sub(r"\b(play|bajao|sunao|gana|music|koi|sa|achcha|pe|par|on)\b", "", text).strip()
            if song:
                return MediaCommands.play_on_youtube(song)
            else:
                return "Kya play karun?"

        # ── Typing & Dictation ────────────────────────────────────────────────
        if any(k in text for k in ["dictation on", "start typing", "typing start", "likhna shuru karo", "type karna shuru karo", "لکھنا شروع کرو"]):
            return DictationMode.turn_on()

        if any(k in text for k in ["dictation off", "stop typing", "likhna band karo", "type karna band karo", "لکھنا بند کرو"]):
            return DictationMode.turn_off()

        if text.startswith("type") or text.startswith("ٹائپ"):
            to_type = text.replace("type", "", 1).replace("karo", "", 1).replace("ٹائپ کرو", "", 1).replace("ٹائپ", "", 1).strip()
            if to_type:
                return TypingCommands.type_text(to_type)
            return "Bataiye kya type karna hai?"

        # -- Keyboard Keys & Shortcuts --
        if text.startswith("press"):
            key = text.replace("press", "").strip()
            return TypingCommands.press_key(key)
        
        shortcuts = ["select all", "copy", "paste", "undo", "redo", "save", "new tab"]
        for s in shortcuts:
            if s in text:
                return TypingCommands.keyboard_shortcut(s)

        # ── Open folder (Search in D drive) ───────────────────────────────────
        if any(k in text for k in ["open folder", "search folder", "folder kholo", "find folder", "folder open"]):
            folder_name = re.sub(r"(please|open folder|search folder|folder kholo|find folder|folder open|named|called|naam ka|ko)", "", text).strip()
            if folder_name:
                return SystemCommands.search_and_open_folder(folder_name)
            return "Kaun sa folder open karun?"

        # ── Open file (Search in D drive) ─────────────────────────────────────
        if any(k in text for k in ["open file", "search file", "file kholo", "find file"]):
            file_name = re.sub(r"(please|open file|search file|file kholo|find file|named|called|naam ki|ko)", "", text).strip()
            if file_name:
                return AdvancedCommands.search_and_open_file(file_name)
            return "Kaun si file open karun?"

        # ── Open app ─────────────────────────────────────────────────────────
        # Matches: "open X", "launch X", "start X", "X open", "X chalao"
        triggers = ["open", "opening", "launch", "start", "run"]
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

        # ── Desktop File/Folder Creation ──────────────────────────────────────
        if any(k in text for k in ["create folder", "make folder", "folder banao", "folder bana do", "folder create"]):
            name = re.sub(r"(please|create folder|make folder|folder banao|folder bana do|folder create|named|called|naam ka|ko)", "", text).strip()
            if not name:
                name = "New Folder"
            return DesktopCommands.create_folder(name)

        if any(k in text for k in ["create file", "make file", "file banao", "file bana do", "file create"]):
            name = re.sub(r"(please|create file|make file|file banao|file bana do|file create|named|called|naam ki|ko)", "", text).strip()
            if not name:
                name = "New File"
            return DesktopCommands.create_file(name)

        # ── Advanced Desktop / Cleaning ───────────────────────────────────────
        if re.search(r"organize\s+(?:my\s+)?desktop|desktop\s+saaf|safai\s+karo", text):
            import winshell
            desktop = winshell.desktop()
            return AdvancedCommands.organize_folder(desktop)

        if any(k in text for k in ["organize downloads", "downloads saaf karo", "downloads organize"]):
            import winshell
            downloads = winshell.folder("downloads")
            return AdvancedCommands.organize_folder(downloads)

        if any(k in text for k in ["organize documents", "documents saaf karo", "documents organize"]):
            import winshell
            docs = winshell.folder("personal")
            return AdvancedCommands.organize_folder(docs)

        if any(k in text for k in ["organize desktop", "desktop organized", "desktop organize", "desktop saaf karo"]):
            import winshell
            desktop = winshell.desktop()
            return AdvancedCommands.organize_folder(desktop)

        if any(k in text for k in ["clean temp", "temp saaf karo", "faltu files khatam karo"]):
            return AdvancedCommands.clean_temp_files()

        # ── Screenshot ────────────────────────────────────────────────────────
        if "screenshot" in text:
            return DesktopCommands.screenshot()

        # ── Note ──────────────────────────────────────────────────────────────
        if re.search(r"\bnote\b", text):
            note = re.sub(r"\b(take notes|take note|note down|note likho|note karo|note)\b", "", text).strip()
            if note:
                return DesktopCommands.take_note(note)
            return "Kya note karna hai?"

        # ── To-Do List ────────────────────────────────────────────────────────
        if "to do" in text or "kaam" in text or "task" in text:
            if any(k in text for k in ["add", "likho", "create"]):
                task = re.sub(r"(add to do|add task|kaam likho|task likho|add|likho|ko)", "", text).strip()
                return AdvancedCommands.todo_manager("add", task)
            if any(k in text for k in ["list", "show", "batao", "dikhao"]):
                return AdvancedCommands.todo_manager("list")
            if any(k in text for k in ["clear", "delete all"]):
                return AdvancedCommands.todo_manager("clear")
            if any(k in text for k in ["done", "complete", "ho gaya"]):
                m = re.search(r"(\d+)", text)
                task_id = m.group(1) if m else None
                return AdvancedCommands.todo_manager("done", task_id)

        # ── Pomodoro ──────────────────────────────────────────────────────────
        if "pomodoro" in text or "focus mode" in text:
            resp = AdvancedCommands.start_pomodoro()
            TimerCommands.set_timer(25 * 60, "Pomodoro Break", on_fire=lambda msg: print(f"[POMODORO] {msg}"))
            return resp

        # ── Clipboard ─────────────────────────────────────────────────────────
        if "clipboard" in text:
            if "get" in text or "batao" in text or "check" in text:
                return AdvancedCommands.clipboard_action("get")
            if "set" in text or "copy" in text:
                content = re.sub(r"(set clipboard|copy to clipboard|copy|clipboard|ko)", "", text).strip()
                return AdvancedCommands.clipboard_action("set", content)

        # ── Window Management ─────────────────────────────────────────────────
        if "window" in text or "bara karo" in text or "chota karo" in text or "band karo" in text:
            if "maximize" in text or "bara karo" in text:
                return AdvancedCommands.window_control("maximize")
            if "minimize all" in text or "screen saaf karo" in text:
                return AdvancedCommands.window_control("minimize_all")
            if "minimize" in text or "chota karo" in text:
                return AdvancedCommands.window_control("minimize")
            if "close" in text or "band karo" in text:
                # Avoid closing shadow if they just say "close"
                if not any(k in text for k in ["shadow", "yourself"]):
                    return AdvancedCommands.window_control("close")

        # ── Time ──────────────────────────────────────────────────────────────
        if any(k in text for k in ["what time", "waqt batao", "time batao"]) or re.search(r"\btime\b", text):
            import time as _t
            return f"Abhi waqt hai {_t.strftime('%I:%M %p')}."

        # ── Joke ──────────────────────────────────────────────────────────────
        if any(k in text for k in ["joke", "funny", "laugh", "latifa"]):
            return ProductivityCommands.tell_joke()

        # ── Weather ───────────────────────────────────────────────────────────
        if "weather" in text or "mausam" in text:
            city = text.split("in")[-1].strip() if " in " in text else "Lahore"
            return ProductivityCommands.get_weather(city)

        # ── Stock / Crypto ────────────────────────────────────────────────────
        if any(k in text for k in ["price", "stock", "share", "crypto"]):
            words = text.split()
            symbol = words[-1].upper() if words else "AAPL"
            return ProductivityCommands.stock_price(symbol)

        # ── Quote ─────────────────────────────────────────────────────────────
        if any(k in text for k in ["quote", "aqwal", "motivation"]):
            if "motivat" in text:
                return AdvancedCommands.get_motivation()
            return ProductivityCommands.get_quote()

        # ── Trash ─────────────────────────────────────────────────────────────
        if any(k in text for k in ["trash", "recycle bin", "empty bin", "bin khali karo", "kuda saaf karo"]):
            return DesktopCommands.empty_trash()

        # ── Search ────────────────────────────────────────────────────────────
        if any(k in text for k in ["search", "searching", "find", "google", "talash karo", "dhundho"]):
            query = re.sub(r"(search for|search on google|search|find|google|talash karo|dhundho)", "", text).strip()
            return WebCommands.search_google(query)

        # ── Play ──────────────────────────────────────────────────────────────
        if "play" in text:
            query = re.sub(r"\b(play on spotify|play on youtube|play karo|bajao|play)\b", "", text).strip()
            return MediaCommands.play_on_youtube(query)

        # ── Project Starters ──────────────────────────────────────────────────
        # Triggers: "create a react project named agency", "create next js project", "create net project"
        if any(k in text for k in ["create", "make", "build", "start", "banao"]) and any(k in text for k in ["project", "app"]):
            frameworks = ["react", "next js", "next", "vue", "angular", "svelte", "vite", "net", "dotnet", "django", "flask", "node", "express"]
            found_framework = None
            for fw in frameworks:
                if fw in text:
                    found_framework = fw
                    break
            
            if found_framework:
                # Extract project name
                # Patterns: "named [name]", "name as [name]", "called [name]", "naam se [name]", "name [name]"
                name_match = re.search(r"(?:named|name as|called|naam se|name|naam)\s+([a-zA-Z0-9_-]+)", text)
                project_name = name_match.group(1) if name_match else "my-project"
                
                return DevCommands.create_project_starter(found_framework, project_name)

        # ── AI Code Generation & Scaffolding ──────────────────────────────────
        if any(k in text for k in ["login page", "login page banao", "login screen"]):
            return DevCommands.create_login_page(raw_text)

        code_triggers = [
            "code a ", "code me ", "write a script", "write a program", 
            "create a program", "build a ", "generate code", 
            "login page", "html page", "python script", "c++ program", "react app"
        ]
        # Check if they are asking to create/code something related to programming
        if any(k in text for k in code_triggers) or (
            any(k in text for k in ["create", "write", "make", "build"]) and 
            any(lang in text for lang in ["html", "python", "c++", "cpp", "javascript", "js", "java", "css", "php", "script", "program", "app", "website"])
        ):
            # Avoid conflict with basic file/folder creation unless language is specified
            is_basic_file = any(k in text for k in ["create file", "make file", "create folder", "make folder"])
            has_lang = any(lang in text for lang in ["html", "python", "c++", "cpp", "javascript", "js", "java", "css", "php"])
            
            if is_basic_file and not has_lang:
                pass # let other handlers or fallback deal with simple file creation
            else:
                return DevCommands.scaffold_project(raw_text)

        # ── Developer ─────────────────────────────────────────────────────────
        if any(k in text for k in ["git status", "git push", "git pull"]):
            return DevCommands.git_status()

        # ── WhatsApp Messaging ─────────────────────────────────────────────────
        # Triggers: "whatsapp", "send message", "message X", "X ko whatsapp"
        if any(k in text for k in ["whatsapp", "send message", "send whatsapp",
                                    "ko whatsapp", "ko message", "text message", "message bhejo", "whatsapp bhejo", "message "]):
            contact, message = MessagingCommands.parse_whatsapp_command(raw_text)
            if contact and message:
                return MessagingCommands.send_whatsapp(contact, message)
            elif contact and not message:
                return f"{contact} ko kya message bhejun?"
            else:
                return ("Bataiye: '[naam] ko WhatsApp karo [message]'")

        if any(k in text for k in ["list contacts", "my contacts", "contacts list",
                                    "contacts batao", "contacts dikhao"]):
            return MessagingCommands.list_contacts()

        # ─────────────────────────────────────────────────────────────────────
        # NEW FEATURES (extra_cmds) — cross-platform
        # ─────────────────────────────────────────────────────────────────────

        # ── Wikipedia ────────────────────────────────────────────────────────
        if text.startswith(("wiki ", "wikipedia ")):
            q = re.sub(r"^(wiki|wikipedia)\s+", "", text).strip("?. ")
            return WikipediaCommands.summary(q)
        if text.startswith("tell me about ") or text.startswith("who is ") or text.startswith("what is "):
            q = re.sub(r"^(tell me about|who is|what is)\s+", "", text).strip("?. ")
            # If it looks like a math expression, defer to calculator below
            if not re.search(r"\d\s*[\+\-\*/x^]\s*\d", q):
                return WikipediaCommands.summary(q)

        # ── Currency conversion (BEFORE unit conversion — currencies are 3-letter codes) ──
        currency_resp = CurrencyCommands.parse_and_convert(text)
        if currency_resp and any(c in text.upper() for c in
                                 ["USD", "EUR", "GBP", "PKR", "INR", "JPY", "CAD", "AUD", "CNY"]):
            return currency_resp

        # ── Unit conversion ──────────────────────────────────────────────────
        if "convert" in text or re.search(r"\d+\s*[a-z]+\s+(?:to|in|into)\s+[a-z]+", text):
            unit_resp = UnitCommands.parse_and_convert(text)
            if unit_resp and "failed" not in unit_resp:
                return unit_resp

        # ── Calculator ───────────────────────────────────────────────────────
        if (text.startswith(("calculate", "calc ", "compute ", "what is "))
                or re.search(r"\d\s*[\+\-\*/x^]\s*\d", text)):
            expr = re.sub(r"^(calculate|calc|compute|what is)\s+", "", text).strip("?. ")
            return CalculatorCommands.evaluate(expr)

        # ── Password generator ───────────────────────────────────────────────
        if re.search(r"generate.*password|create.*password|new\s+password", text):
            m = re.search(r"(\d+)", text)
            length = int(m.group(1)) if m else 16
            return PasswordCommands.generate(length)

        # ── Timer / alarm / reminder ──────────────────────────────────────────
        if any(k in text for k in ["set timer", "start timer", "set alarm", "remind me", "reminder", "yad dilana", "yad dilao"]):
            secs = TimerCommands.parse_duration(text)
            
            # If duration is missing, but "remind" was said, enter a simple wizard mode
            if not secs:
                if any(k in text for k in ["remind me", "reminder", "yad dilao"]):
                    return "Zaroor! Kis cheez ke baare mein aur kab yaad dilaun? (e.g. 'call mom in 5 minutes')"
                return "Zaroor, lekin kitni der baad? (e.g. '5 minutes' ya 'at 10pm')"

            # Label extraction
            lbl_text = text
            for noise in ["set timer for", "set timer", "start timer", "set alarm for", "set alarm", "set a reminder for", "set a reminder", "create a reminder",
                         "remind me to", "remind me that", "remind me", "reminder for", "reminder", "yad dilana", "yad dilao"]:
                lbl_text = lbl_text.replace(noise, "")
            
            time_units = r"\d+\s*(hour|hr|minute|min|second|sec|pm|am|at|baje|o'clock)s?"
            label = re.sub(time_units, "", lbl_text).strip()
            # Clean up grammar noise
            label = re.sub(r"\bin\b|\bat\b|\bfor\b|\bto\b", "", label).strip()
            
            if not label: label = "reminder"
            
            def _on_timer_fire(msg):
                if hasattr(self.hud, "reminder_signal"):
                    self.hud.reminder_signal.emit(label)
                tts_engine.speak(f"[EXCITED] {msg}")
                
            return TimerCommands.set_timer(secs, label, on_fire=_on_timer_fire)
                
        if "list timers" in text or "active timers" in text or "show timers" in text or "tasks batao" in text:
            return TimerCommands.list_active()

        if any(k in text for k in ["cancel reminder", "delete reminder", "remove reminder", "stop alarm", "delete alarm"]):
            # Try to extract index or name
            m = re.search(r"(\d+)", text)
            target = m.group(1) if m else text.replace("cancel reminder", "").replace("delete reminder", "").strip()
            # If target is empty, ask which one
            if not target:
                return "Kaun sa reminder cancel karun? (Aap number ya naam bata sakte hain)"
            
            # Simple wrapper to handle indices
            try:
                idx = int(target) - 1
                timers = [t for t in TimerCommands._timers if t["fires_at"] > datetime.now()]
                if 0 <= idx < len(timers):
                    label = timers[idx]["label"]
                    timers[idx]["timer"].cancel()
                    TimerCommands._timers.remove(timers[idx])
                    TimerCommands._save_reminders()
                    self.hud.refresh_reminders()
                    return f"Theek hai, '{label}' reminder cancel kar diya hai."
            except:
                pass
                
            # Try by name
            for t in TimerCommands._timers:
                if t["label"].lower() in target.lower() or target.lower() in t["label"].lower():
                    t["timer"].cancel()
                    TimerCommands._timers.remove(t)
                    TimerCommands._save_reminders()
                    self.hud.refresh_reminders()
                    return f"Theek hai, '{t['label']}' reminder cancel kar diya hai."
            
            return f"Mujhe '{target}' naam ka koi active reminder nahi mila."

        # ── Coin / dice / fact ───────────────────────────────────────────────
        if "flip" in text and "coin" in text:
            return FunCommands.coin_flip()
        if "roll" in text and ("dice" in text or "die" in text):
            m = re.search(r"(\d+)\s*d\s*(\d+)", text)
            if m:
                return FunCommands.dice_roll(int(m.group(2)), int(m.group(1)))
            sides_m = re.search(r"d\s*(\d+)", text)
            return FunCommands.dice_roll(int(sides_m.group(1)) if sides_m else 6)
        if "random fact" in text or "fun fact" in text or "tell me a fact" in text:
            return FunCommands.random_fact()

        # ── News headlines ───────────────────────────────────────────────────
        if any(k in text for k in ["news", "headlines", "what's happening"]):
            return NewsCommands.headlines()

        # ── Translation ───────────────────────────────────────────────────────
        if "translate" in text or "urdu mein" in text or "english mein" in text:
            target = 'ur' if 'urdu' in text else 'en'
            content = re.sub(r"(translate|to urdu|to english|urdu mein|english mein|karo|batao)", "", text).strip()
            if content:
                return AdvancedCommands.translate_text(content, target)
            return "Bataiye kya translate karna hai?"

        # ── Close Specific App ────────────────────────────────────────────────
        if re.search(r"\bclose\b", text) and not any(k in text for k in ["close shadow", "close yourself", "pc band karo"]):
            app_to_close = re.sub(r"\b(close|band karo|ko)\b", "", text).strip()
            if app_to_close:
                return AdvancedCommands.close_app(app_to_close)

        # ── App Volume ────────────────────────────────────────────────────────
        if "volume" in text and any(k in text for k in ["set", "make", "karo"]):
            m = re.search(r"(?:set|make)\s+([a-zA-Z]+)\s+volume\s+to\s+(\d+)", text)
            if m:
                app, vol = m.group(1), int(m.group(2))
                return AdvancedCommands.set_app_volume(app, vol / 100.0)

        # ── Email ─────────────────────────────────────────────────────────────
        if any(k in text for k in ["email", "mail"]):
            if "send" in text:
                # Basic parsing for "send email to X with subject Y and message Z"
                # This is a bit complex for regex, usually handled better by AI if local fails
                m = re.search(r"send\s+(?:email|mail)\s+to\s+([a-zA-Z0-9@._-]+)\s+subject\s+(.+?)\s+message\s+(.+)", text)
                if m:
                    return AdvancedCommands.send_email(m.group(1), m.group(2), m.group(3))

        # ── Generic Stop ──────────────────────────────────────────────────────
        if any(k in text for k in ["stop", "band karo", "ruk jao"]):
            return "Kaam rok diya gaya hai."

        # ── AI Fallback ───────────────────────────────────────────────────────
        print("[DISPATCH] No local match -> AI fallback")
        return ai_brain.get_response(raw_text, stream=True)
