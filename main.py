import sys
import os

# Force UTF-8 output so emoji/unicode prints don't crash on Windows console
# If running without a console (PyInstaller --noconsole), sys.stdout/stderr will be None.
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
elif getattr(sys.stdout, 'encoding', '') != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
elif getattr(sys.stderr, 'encoding', '') != 'utf-8':
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
    response_ready = pyqtSignal(str)
    status_update = pyqtSignal(str)
    settings_requested = pyqtSignal()

class AntiGravityApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.hud = HUDWindow(config_manager)
        self.settings = SettingsWindow(self.hud)
        self.dispatcher = CommandDispatcher(self.hud)

        # Thread-safe signals: worker thread -> main Qt thread
        self.signals = VoiceSignal()
        self.signals.command_received.connect(self.handle_command)
        self.signals.response_ready.connect(self.finalize_response)
        self.signals.status_update.connect(self.hud.set_status)
        self.signals.settings_requested.connect(self.settings.show)

        self.listener = Listener(self.signals.command_received.emit)

        self.tray = TrayIcon(self.hud, self.app)
        self.tray.start()
        self.tray._open_settings = self.signals.settings_requested.emit
        self.hud._settings_callback = self.signals.settings_requested.emit

        # Warm psutil so the first non-blocking sample isn't 0%.
        psutil.cpu_percent(interval=None)

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1500)  # snappier HUD refresh (was 2000ms)

        self.hud.show()
        
        # Load persistent reminders
        from commands.extra_cmds import TimerCommands
        TimerCommands.load_reminders(on_fire_callback=lambda msg: tts_engine.speak(f"[EXCITED] {msg}"))
        
        tts_engine.speak("System online. All systems operational.")
        self.listener.start()

    def update_stats(self):
        # interval=None → returns delta since the previous call (non-blocking).
        # This keeps the Qt event loop responsive instead of pausing it.
        cpu = psutil.cpu_percent(interval=None)
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
        self.hud.set_status("THINKING")
        self.hud.set_command(text)

        # Run dispatch in a background thread to keep UI responsive
        def _worker_task():
            try:
                # Dispatch the command (might take seconds)
                response = self.dispatcher.dispatch(text)
                self.signals.response_ready.emit(response)
            except Exception as e:
                print(f"[ERROR] {e}")
                self.signals.response_ready.emit(f"Command error: {str(e)}")

        threading.Thread(target=_worker_task, daemon=True).start()

    def finalize_response(self, response):
        def extract_emotion(text):
            for emotion in ["HAPPY", "SAD", "EXCITED", "ANGRY", "CURIOUS", "CALM"]:
                tag = f"[{emotion}]"
                if text.startswith(tag):
                    return emotion, text[len(tag):].strip()
            return "CALM", text

        self.hud.set_status("SPEAKING")
        
        if isinstance(response, str):
            emotion, clean_text = extract_emotion(response)
            print(f"[RESPONSE] {clean_text} (Emotion: {emotion})")
            self.hud.set_emotion(emotion)
            self.hud.set_response(clean_text)
            tts_engine.speak(response) # TTS engine handles the tag itself for modulation
        else:
            # It's a generator (streaming AI)
            full_response = ""
            first_chunk = True
            for sentence in response:
                if not sentence: continue
                
                if first_chunk:
                    emotion, _ = extract_emotion(sentence)
                    self.hud.set_emotion(emotion)
                    first_chunk = False
                
                print(f"[STREAM] {sentence}")
                full_response += sentence + " "
                
                # Update response text in HUD (stripping tags for display)
                display_text = full_response
                for tag in ["[HAPPY]", "[SAD]", "[EXCITED]", "[ANGRY]", "[CURIOUS]", "[CALM]"]:
                    display_text = display_text.replace(tag, "")
                
                self.hud.set_response(display_text.strip())
                tts_engine.speak(sentence)
            print(f"[RESPONSE COMPLETE]")
        
        print(f"{'='*50}\n")
        print("[LISTENING] Back to listening...")

        # Reset status after some time
        QTimer.singleShot(4000, lambda: self.hud.set_status("IDLE"))

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = AntiGravityApp()
    app.run()
