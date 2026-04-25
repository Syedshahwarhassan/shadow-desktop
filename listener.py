import speech_recognition as sr
import threading
import queue
import time
from config_manager import config_manager

# Common mishearings of "shadow"
WAKE_WORD_VARIANTS = [
    "shadow", "shado", "shader", "shaddow", "shadoe",
    "اسکول", "اسکرول", "کال", # Urdu mishearings handled here if needed, but mostly for wake word
    "\u0634\u06cc\u0688\u0648", "\u0634\u062f\u0648", 
]

class Listener:
    def __init__(self, callback):
        self.recognizer   = sr.Recognizer()
        self.microphone   = sr.Microphone()
        self.callback     = callback
        self.is_listening = False
        self._stop_fn     = None
        self._audio_queue = queue.Queue()
        self.session_active_until = 0
        
        # Session tracking removed

        self.recognizer.energy_threshold        = 250
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold          = 0.6
        self.recognizer.non_speaking_duration    = 0.4

        print("[INIT] Calibrating microphone...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[INIT] Microphone ready.")

    def start(self):
        self.is_listening = True
        self._stop_fn = self.recognizer.listen_in_background(
            self.microphone,
            self._audio_callback,
            phrase_time_limit=8
        )
        threading.Thread(target=self._process_loop, daemon=True).start()
        print("[INIT] Listening... (say 'shadow' along with your command)")

    def _audio_callback(self, recognizer, audio):
        self._audio_queue.put(audio)

    def _process_loop(self):
        while self.is_listening:
            try:
                audio = self._audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            text_en, text_ur = self._recognize_parallel(audio)
            
            # Use the most confident result
            raw_text = text_en if text_en else text_ur
            if not raw_text: continue

            wake_word = config_manager.get("wake_word", "shadow").lower()
            
            # If DictationMode is active, bypass wake word requirement
            from commands.typing_cmds import DictationMode
            if DictationMode.is_active():
                # We can strip the wake word if they accidentally said it while dictating
                clean_text = raw_text
                matched_wake = self._find_wake(text_en, text_ur, wake_word)
                if matched_wake:
                    parts = matched_wake.split(wake_word, 1)
                    clean_text = parts[1].strip() if len(parts) > 1 else clean_text
                
                if clean_text:
                    print(f"[STT DICTATION] Heard: {clean_text}")
                    self.callback(clean_text)
                continue

            matched_wake = self._find_wake(text_en, text_ur, wake_word)

            if matched_wake:
                # Interrupt any ongoing TTS speech immediately
                from tts import tts_engine
                tts_engine.stop()

                print(f"[STT] Heard: {raw_text}")
                parts = matched_wake.split(wake_word, 1)
                command = parts[1].strip() if len(parts) > 1 else ""

                if command:
                    self.session_active_until = 0
                    self.callback(command)
                else:
                    self.session_active_until = time.time() + 8.0
                    self.callback("_WAKE_")
            elif time.time() < self.session_active_until:
                print(f"[STT] Heard (In Session): {raw_text}")
                from tts import tts_engine
                tts_engine.stop()
                
                self.session_active_until = 0
                self.callback(raw_text)

    def _find_wake(self, text_en, text_ur, wake_word):
        for text in [text_en, text_ur]:
            if not text: continue
            if wake_word in text: return text
            for v in WAKE_WORD_VARIANTS:
                if v in text:
                    print(f"  -> Wake variant matched: {v}")
                    return text.replace(v, wake_word, 1)
        return ""

    def _recognize_parallel(self, audio):
        # Fan out EN/UR recognizers in parallel and return as soon as ONE
        # of them produces a result (instead of waiting up to 14s for both).
        results = {"en": "", "ur": ""}
        done = threading.Event()

        def _recog(lang, key):
            try:
                results[key] = self.recognizer.recognize_google(audio, language=lang).lower()
            except Exception:
                pass
            finally:
                if results[key]:
                    done.set()

        t1 = threading.Thread(target=_recog, args=("en-US", "en"), daemon=True)
        t2 = threading.Thread(target=_recog, args=("ur-PK", "ur"), daemon=True)
        t1.start(); t2.start()

        # First-result wins (up to 5s); briefly wait for the other so the
        # dispatcher can pick the more confident transcript when both arrive.
        done.wait(timeout=5)
        t1.join(timeout=0.4); t2.join(timeout=0.4)
        return results["en"], results["ur"]
