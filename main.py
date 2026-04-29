import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
elif getattr(sys.stdout, "encoding", "") != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
elif getattr(sys.stderr, "encoding", "") != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import re
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon
import keyboard
import ctypes

# Fix High DPI scaling and "Access is denied" warnings on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from hud import ShadowHUD
from listener import Listener
from tts import tts_engine
from commands import CommandDispatcher
from config_manager import config_manager
from tray import TrayIcon
from settings_ui import SettingsWindow
from performance_logger import timeit

# Pre-compiled emotion patterns (module-level, not per-call)
_EMOTION_TAGS  = frozenset(["HAPPY", "SAD", "EXCITED", "ANGRY", "CURIOUS", "CALM"])
_TAG_RE        = re.compile(r"^\[(" + "|".join(_EMOTION_TAGS) + r")\]\s*", re.IGNORECASE)
_STRIP_TAGS_RE = re.compile(r"\[(?:" + "|".join(_EMOTION_TAGS) + r")\]", re.IGNORECASE)

def _extract_emotion(text: str) -> tuple[str, str]:
    m = _TAG_RE.match(text)
    if m:
        return m.group(1).upper(), text[m.end():]
    return "CALM", text

class VoiceSignal(QObject):
    command_received    = pyqtSignal(str)
    response_ready      = pyqtSignal(object)
    status_update       = pyqtSignal(str)
    settings_requested  = pyqtSignal()
    transcript_received = pyqtSignal(str)

class AntiGravityApp:
    def __init__(self):
        self.app        = QApplication(sys.argv)
        self.app.setApplicationName("Shadow")
        
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo.ico")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))

        self.hud        = ShadowHUD(config_manager)
        self.settings   = SettingsWindow(self.hud)
        self.dispatcher = CommandDispatcher(self.hud)

        self.signals = VoiceSignal()
        self.signals.command_received.connect(self.handle_command)
        self.signals.response_ready.connect(self.finalize_response)
        self.signals.status_update.connect(self._update_hud_status)
        self.signals.settings_requested.connect(self.settings.show)
        self.signals.transcript_received.connect(self.hud.update_transcript)

        self.listener = Listener(self.signals.command_received.emit, self.signals.status_update.emit, self.signals.transcript_received.emit)

        self.tray = TrayIcon(self.hud, self.app)
        self.tray.start()
        self.tray._open_settings    = self.signals.settings_requested.emit
        self.hud._settings_callback = self.signals.settings_requested.emit
        self.hud._mute_callback     = self.listener.toggle_wake_word

        self._dispatch_pool  = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dispatch")
        self._active_cmd_id  = 0

        psutil.cpu_percent(interval=None)
        # Stats are now handled by ShadowHUD's internal timers
        # No need for stats_timer here

        # Initialize HUD status indicators
        self.hud.set_status("STT", config_manager.get("stt_mode", "local"), "ok")
        self.hud.set_status("LLM", config_manager.get("llm_model", "gpt-4o"), "ok")
        self.hud.set_status("TTS", config_manager.get("tts_mode", "kokoro"), "ok")
        self.hud.set_status("WAKE", "ON", "ok")

        # ── Reminders ─────────────────────────────────────────────────────────
        from commands.extra_cmds import TimerCommands
        TimerCommands.load_reminders(on_fire_callback=lambda msg: tts_engine.speak(f"[EXCITED] {msg}"))
        tts_engine.speak("System online. All systems operational.")
        self.listener.start()
        
        hotkey      = config_manager.get("hotkey", "win+shift+s")
        exit_hotkey = config_manager.get("exit_hotkey", "ctrl+shift+q")

        try:
            keyboard.add_hotkey(hotkey, self.toggle_visibility)
            keyboard.add_hotkey(exit_hotkey, self.cleanup)
            print(f"[INIT] Visibility hotkey: {hotkey}")
            print(f"[INIT] Emergency exit hotkey: {exit_hotkey}")
        except Exception as e:
            print(f"[ERR] Failed to bind hotkeys: {e}")

        if config_manager.get("hud_visible_on_start", True):
            self.hud.show_hud()


    def toggle_visibility(self) -> None:
        if self.hud.isVisible() and self.hud.windowOpacity() > 0.1:
            self.hud.hide_hud()
        else:
            self.hud.show_hud()

    def update_stats(self) -> None:
        pass # Handled by ShadowHUD internally

    def _update_hud_status(self, status: str) -> None:
        if status == "LISTENING":
            self.hud.set_listening(True)
        elif status == "THINKING":
            self.hud.set_processing(True)
        elif status == "IDLE":
            self.hud.set_processing(False)
            self.hud.set_listening(False)
        elif status == "SPEAKING":
            # Optional: handle speaking mode if needed
            pass

    def handle_command(self, text: str) -> None:
        self.hud.show_hud()
        if text == "_WAKE_":
            self.hud.set_listening(True)
            tts_engine.speak("Yes?")
            return
        print(f"\n{'='*50}\n[COMMAND] '{text}'")
        self.hud.set_processing(True)
        self.hud.update_transcript(text)
        self.last_command_text = text
        self._active_cmd_id += 1
        cmd_id = self._active_cmd_id

        @timeit
        def _task():
            try:
                response = self.dispatcher.dispatch(text)
                if cmd_id == self._active_cmd_id:
                    self.signals.response_ready.emit(response)
            except Exception as e:
                print(f"[ERROR] {e}")
                if cmd_id == self._active_cmd_id:
                    self.signals.response_ready.emit(f"Command error: {str(e)}")

        try:
            if getattr(self, "_shutting_down", False): return
            self._dispatch_pool.submit(_task)
        except RuntimeError: pass

    def finalize_response(self, response) -> None:
        self.hud.set_processing(False)
        if isinstance(response, str):
            emotion, clean = _extract_emotion(response)
            print(f"[RESPONSE] {clean}  (Emotion: {emotion})")
            self.hud.update_transcript(clean)
            self.hud.add_log_entry(self.last_command_text if hasattr(self, "last_command_text") else "cmd", clean[:30]+"...")
            tts_engine.speak(response)
        else:
            full, first = "", True
            for sentence in response:
                if not sentence: continue
                if first:
                    emotion, _ = _extract_emotion(sentence)
                    first = False
                print(f"[STREAM] {sentence}")
                full += sentence + " "
                self.hud.update_transcript(_STRIP_TAGS_RE.sub("", full).strip())
                tts_engine.speak(sentence)
            print("[RESPONSE COMPLETE]")
        print(f"{'='*50}\n[LISTENING] Back to listening…")
        self._update_hud_status("IDLE")

    def run(self) -> None:
        try: self.app.exec()
        finally: self.cleanup()

    def cleanup(self) -> None:
        self._shutting_down = True
        print("[SHUTDOWN] Cleaning up...")
        if hasattr(self, 'listener'): self.listener.stop()
        self._dispatch_pool.shutdown(wait=False)
        os._exit(0)

if __name__ == "__main__":
    AntiGravityApp().run()
