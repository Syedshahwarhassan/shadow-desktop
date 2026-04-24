import sys
import os

# Force UTF-8 output so emoji/unicode prints don't crash on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import psutil
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from hud import HUDWindow
from listener import Listener
from tts import tts_engine
from commands import CommandDispatcher
from config_manager import config_manager
from tray import TrayIcon
from settings_ui import SettingsWindow

COMMAND_TIMEOUT = 20  # seconds before giving up on a command

class VoiceSignal(QObject):
    command_received = pyqtSignal(str)

class AntiGravityApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.hud = HUDWindow(config_manager)
        self.settings = SettingsWindow(self.hud)
        self.dispatcher = CommandDispatcher(self.hud)

        # Thread-safe signal: listener thread -> main Qt thread
        self.signals = VoiceSignal()
        self.signals.command_received.connect(self.handle_command)

        self.listener = Listener(self.signals.command_received.emit)

        self.tray = TrayIcon(self.hud, self.app)
        self.tray.start()
        self.tray._open_settings = self.settings.show

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

        self.hud.show()
        name = config_manager.get('assistant_name', 'Shadow')
        tts_engine.speak(f"{name} online. All systems operational.")
        self.listener.start()

    def update_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.hud.update_stats(cpu, ram)

    def handle_command(self, text):
        if text == "_WAKE_":
            print("[STATUS] Wake word detected - Waiting for command...")
            self.hud.set_status("LISTENING")
            tts_engine.speak("Yes?")
            return

        print(f"\n{'='*50}")
        print(f"[COMMAND] Processing: '{text}'")
        self.hud.set_status("SPEAKING")
        self.hud.set_command(text)

        # Run dispatch in a worker thread with timeout
        result = {"response": None}

        def _run():
            try:
                result["response"] = self.dispatcher.dispatch(text)
            except Exception as e:
                result["response"] = f"Command error: {str(e)}"
                print(f"[ERROR] {e}")

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=COMMAND_TIMEOUT)

        if worker.is_alive() or result["response"] is None:
            response = "I could not process that. Please try again."
            print(f"[TIMEOUT] Command timed out after {COMMAND_TIMEOUT}s")
        else:
            response = result["response"]
            print(f"[RESPONSE] {response}")

        self.hud.set_response(response)
        tts_engine.speak(response)
        print(f"{'='*50}\n")
        print("[LISTENING] Back to listening...")

        QTimer.singleShot(3000, lambda: self.hud.set_status("IDLE"))

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = AntiGravityApp()
    app.run()
