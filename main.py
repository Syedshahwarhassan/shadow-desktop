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
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from hud import HUDWindow
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
    command_received   = pyqtSignal(str)
    response_ready     = pyqtSignal(object)
    status_update      = pyqtSignal(str)
    settings_requested = pyqtSignal()


class AntiGravityApp:
    def __init__(self):
        self.app        = QApplication(sys.argv)
        self.hud        = HUDWindow(config_manager)
        self.settings   = SettingsWindow(self.hud)
        self.dispatcher = CommandDispatcher(self.hud)

        self.signals = VoiceSignal()
        self.signals.command_received.connect(self.handle_command)
        self.signals.response_ready.connect(self.finalize_response)
        self.signals.status_update.connect(self.hud.set_status)
        self.signals.settings_requested.connect(self.settings.show)

        self.listener = Listener(self.signals.command_received.emit)

        self.tray = TrayIcon(self.hud, self.app)
        self.tray.start()
        self.tray._open_settings    = self.signals.settings_requested.emit
        self.hud._settings_callback = self.signals.settings_requested.emit

        # Persistent pool — no thread-creation overhead per command
        self._dispatch_pool  = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dispatch")
        self._active_cmd_id  = 0

        psutil.cpu_percent(interval=None)
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1500)

        self.hud.show()

        from commands.extra_cmds import TimerCommands
        TimerCommands.load_reminders(
            on_fire_callback=lambda msg: tts_engine.speak(f"[EXCITED] {msg}")
        )
        tts_engine.speak("System online. All systems operational.")
        self.listener.start()

    def update_stats(self) -> None:
        self.hud.update_stats(psutil.cpu_percent(interval=None),
                              psutil.virtual_memory().percent)

    def handle_command(self, text: str) -> None:
        if text == "_WAKE_":
            print("[STATUS] Wake word — waiting for command…")
            self.hud.set_status("LISTENING")
            tts_engine.speak("Yes?")
            return

        print(f"\n{'='*50}\n[COMMAND] '{text}'")
        self.hud.set_status("THINKING")
        self.hud.set_command(text)

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

        self._dispatch_pool.submit(_task)

    def finalize_response(self, response) -> None:
        self.hud.set_status("SPEAKING")

        if isinstance(response, str):
            emotion, clean = _extract_emotion(response)
            print(f"[RESPONSE] {clean}  (Emotion: {emotion})")
            self.hud.set_emotion(emotion)
            self.hud.set_response(clean)
            tts_engine.speak(response)
        else:
            full, first = "", True
            for sentence in response:
                if not sentence:
                    continue
                if first:
                    emotion, _ = _extract_emotion(sentence)
                    self.hud.set_emotion(emotion)
                    first = False
                print(f"[STREAM] {sentence}")
                full += sentence + " "
                self.hud.set_response(_STRIP_TAGS_RE.sub("", full).strip())
                tts_engine.speak(sentence)
            print("[RESPONSE COMPLETE]")

        print(f"{'='*50}\n[LISTENING] Back to listening…")
        QTimer.singleShot(4000, lambda: self.hud.set_status("IDLE"))

    def run(self) -> None:
        sys.exit(self.app.exec())


if __name__ == "__main__":
    AntiGravityApp().run()
