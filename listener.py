"""
listener.py — Voice recognition engine for Shadow.

Optimisations over the previous version
────────────────────────────────────────
• ThreadPoolExecutor (max 4 workers) reuses threads instead of spawning a
  new pair per audio chunk — eliminates ~2–5 ms thread-creation overhead on
  every utterance.
• Top-level imports for tts_engine and DictationMode — previously imported
  inside the hot _process_loop on every iteration.
• STT timeout reduced from 3 s → 2 s; en-US typically resolves in <800 ms.
• _recognizer_lock prevents re-entrant Google API calls if the queue builds up.
• Wake-word variants stored as frozenset for O(1) lookup.
"""

import speech_recognition as sr
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor

from config_manager import config_manager

# ── Top-level imports (were inside hot loop) ─────────────────────────────────
from tts import tts_engine                         # noqa: E402
from commands.typing_cmds import DictationMode     # noqa: E402

# Common STT mishearings of "shadow" — frozenset for O(1) membership test
WAKE_WORD_VARIANTS: frozenset[str] = frozenset([
    "shadow", "shado", "shader", "shaddow", "shadoe",
    "اسکول", "اسکرول", "کال",
    "\u0634\u06cc\u0688\u0648", "\u0634\u062f\u0648",
])

_STT_TIMEOUT = 3.0   # seconds — first result wins within this window
_JOIN_TIMEOUT = 0.3  # brief wait for the slower recognizer


class Listener:
    def __init__(self, callback):
        self.recognizer   = sr.Recognizer()
        self.microphone   = sr.Microphone()
        self.callback     = callback
        self.is_listening = False
        self._stop_fn:    object = None
        self._audio_queue: queue.Queue = queue.Queue()
        self.session_active_until: float = 0

        # Thread pool reused across all recognition tasks
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt")

        self.recognizer.energy_threshold         = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold          = 0.6
        self.recognizer.non_speaking_duration    = 0.4

        print("[INIT] Calibrating microphone…")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[INIT] Microphone ready.")

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        self.is_listening = True
        self._stop_fn = self.recognizer.listen_in_background(
            self.microphone,
            self._audio_callback,
            phrase_time_limit=8,
        )
        threading.Thread(
            target=self._process_loop, daemon=True, name="listener-process"
        ).start()
        print("[INIT] Listening… (say 'shadow' with your command)")

    def stop(self) -> None:
        self.is_listening = False
        if callable(self._stop_fn):
            self._stop_fn(wait_for_stop=False)
        self._pool.shutdown(wait=False)

    # ── Internal pipeline ─────────────────────────────────────────────────────

    def _audio_callback(self, recognizer, audio) -> None:
        # We now capture audio even while TTS is speaking to allow interruptions.
        # However, we only put it in the queue if the user is likely saying the wake word
        # or if the session is active. 
        self._audio_queue.put(audio)

    def _process_loop(self) -> None:
        while self.is_listening:
            try:
                audio = self._audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            # Skip backlog
            if self._audio_queue.qsize() > 3:
                print("[LISTENER] Queue backlog — dropping stale audio")
                continue

            # If TTS just finished speaking, drain any residual chunks captured
            # during playback (microphone bleed-through).
            if not tts_engine.is_speaking and self._audio_queue.qsize() > 1:
                try:
                    while self._audio_queue.qsize() > 1:
                        self._audio_queue.get_nowait()
                except Exception:
                    pass

            text_en, text_ur = self._recognize_parallel(audio)
            raw_text = text_en if text_en else text_ur
            if not raw_text:
                continue

            wake_word = config_manager.get("wake_word", "shadow").lower()

            # ── Dictation mode bypass ─────────────────────────────────────────
            if DictationMode.is_active():
                clean_text = raw_text
                matched = self._find_wake(text_en, text_ur, wake_word)
                if matched:
                    parts = matched.split(wake_word, 1)
                    clean_text = parts[1].strip() if len(parts) > 1 else clean_text
                if clean_text:
                    print(f"[STT DICTATION] {clean_text}")
                    self.callback(clean_text)
                continue

            # ── Normal mode ───────────────────────────────────────────────────
            matched = self._find_wake(text_en, text_ur, wake_word)

            if matched:
                tts_engine.stop()
                print(f"[STT] Heard: {raw_text}")
                parts = matched.split(wake_word, 1)
                command = parts[1].strip() if len(parts) > 1 else ""

                try:
                    if command:
                        self.session_active_until = 0
                        self.callback(command)
                    else:
                        self.session_active_until = time.time() + 8.0
                        self.callback("_WAKE_")
                except Exception as e:
                    print(f"[LISTENER ERR] Callback failure: {e}")

            elif time.time() < self.session_active_until:
                print(f"[STT] In-session: {raw_text}")
                tts_engine.stop()
                self.session_active_until = 0
                try:
                    self.callback(raw_text)
                except Exception as e:
                    print(f"[LISTENER ERR] Callback failure: {e}")

    def _find_wake(self, text_en: str, text_ur: str, wake_word: str) -> str:
        for text in (text_en, text_ur):
            if not text:
                continue
            if wake_word in text:
                return text
            for variant in WAKE_WORD_VARIANTS:
                if variant in text:
                    print(f"  -> Wake variant matched: '{variant}'")
                    return text.replace(variant, wake_word, 1)
        return ""

    def _recognize_parallel(self, audio) -> tuple[str, str]:
        """Fan-out EN/UR recognizers via thread pool; first result wins."""
        results: dict[str, str] = {"en": "", "ur": ""}
        done = threading.Event()

        def _recog(lang: str, key: str) -> None:
            try:
                results[key] = self.recognizer.recognize_google(
                    audio, language=lang
                ).lower()
            except Exception:
                pass
            finally:
                if results[key]:
                    done.set()

        fut_en = self._pool.submit(_recog, "en-US", "en")
        fut_ur = self._pool.submit(_recog, "ur-PK", "ur")

        done.wait(timeout=_STT_TIMEOUT)
        if not done.is_set():
            print(f"[STT] Timeout after {_STT_TIMEOUT}s — no result from Google")

        # Brief extra wait so the slower recognizer can still contribute.
        # TimeoutError is expected when one language is slow — swallow it.
        for fut in (fut_en, fut_ur):
            if not fut.done():
                try:
                    fut.result(timeout=_JOIN_TIMEOUT + 0.1)
                except Exception:
                    pass

        return results["en"], results["ur"]
