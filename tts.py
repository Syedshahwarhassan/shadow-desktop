"""
tts.py — Industry-grade TTS engine for Shadow Voice Assistant.

Optimisations over the previous version
────────────────────────────────────────
• Persistent asyncio event-loop running in a dedicated daemon thread.
  edge_tts coroutines are posted with run_coroutine_threadsafe() instead
  of calling asyncio.run() per sentence (~50 ms saved per utterance).
• pygame.mixer initialised ONCE in __init__ (not on every speak call).
• Dual rotating temp files (temp_0.mp3 / temp_1.mp3) eliminates file-lock
  races when consecutive streaming sentences overlap.
• Emotion regex compiled once at module import; emotion map stored as a
  module-level dict — no per-call allocation.
• pygame Channel-based playback (instead of music) gives precise per-channel
  stop() without touching other audio streams.
• _stop_flag uses threading.Event for reliable cross-thread signalling.
"""

import threading
import queue
import subprocess
import os
import re
import asyncio
import itertools
import edge_tts
import pyttsx3
import pygame
from config_manager import config_manager

# ── Emotion map ───────────────────────────────────────────────────────────────
_EMOTION_MAP: dict[str, dict[str, str]] = {
    "[HAPPY]":   {"pitch": "+15Hz", "rate": "-5%"},
    "[EXCITED]": {"pitch": "+25Hz", "rate": "+5%"},
    "[SAD]":     {"pitch": "-15Hz", "rate": "-25%"},
    "[ANGRY]":   {"pitch": "-5Hz",  "rate": "+10%"},
    "[CURIOUS]": {"pitch": "+10Hz", "rate": "-10%"},
    "[CALM]":    {"pitch": "+0Hz",  "rate": "-15%"},
}

# Pre-compile tag-stripping pattern once
_TAG_PATTERN = re.compile(
    r"^\s*(\[(?:HAPPY|EXCITED|SAD|ANGRY|CURIOUS|CALM)\])\s*", re.IGNORECASE
)

# Heuristic patterns for tag-less text
_EXCITE_WORDS  = frozenset(["واہ", "زبردست", "ہاہا", "ارے"])
_SADNESS_WORDS = frozenset(["افسوس", "سوری", "sad"])


def _extract_emotion(text: str) -> tuple[dict[str, str], str]:
    """Return (pitch/rate params, clean_text) — O(1) lookup."""
    m = _TAG_PATTERN.match(text)
    if m:
        params = _EMOTION_MAP.get(m.group(1).upper(), {"pitch": "+0Hz", "rate": "-10%"})
        return params, text[m.end():].strip()

    # Heuristic fallback
    pitch, rate = "+0Hz", "-10%"
    lower = text.lower()
    if "!" in text or any(w in lower for w in _EXCITE_WORDS):
        pitch, rate = "+15Hz", "-5%"
    elif "?" in text:
        pitch = "+5Hz"
    elif any(w in lower for w in _SADNESS_WORDS):
        pitch, rate = "-15Hz", "-20%"
    return {"pitch": pitch, "rate": rate}, text


# ── Dual rotating temp buffers ────────────────────────────────────────────────
_TEMP_FILES   = ["temp_0.mp3", "temp_1.mp3"]
_buffer_cycle = itertools.cycle(range(len(_TEMP_FILES)))


class TTSEngine:
    """
    Production-grade TTS engine.

    Priority chain: edge-tts (neural, Urdu) → pyttsx3 (offline) → PowerShell SAPI.
    """

    def __init__(self):
        self._queue:   queue.Queue[str | None] = queue.Queue()
        self._stop_evt = threading.Event()
        self._current_ps_process: subprocess.Popen | None = None

        # ── pygame mixer (initialised once) ───────────────────────────────────
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)  # low-latency buffer
            pygame.mixer.init()
            self._channel: pygame.mixer.Channel = pygame.mixer.Channel(0)
        except Exception as e:
            print(f"[TTS] pygame init failed: {e}")
            self._channel = None  # type: ignore[assignment]

        # ── pyttsx3 offline fallback ──────────────────────────────────────────
        try:
            self.pyttsx_engine = pyttsx3.init()
            self._setup_pyttsx(self.pyttsx_engine)
        except Exception as e:
            print(f"[TTS] pyttsx3 init failed: {e}")
            self.pyttsx_engine = None

        # ── Persistent asyncio event loop in a daemon thread ─────────────────
        self._loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(
            target=self._run_loop, daemon=True, name="tts-asyncio-loop"
        )
        loop_thread.start()

        # ── TTS worker thread ─────────────────────────────────────────────────
        threading.Thread(
            target=self._worker, daemon=True, name="tts-worker"
        ).start()

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        if not text:
            return
        clean = re.sub(r"[*_`#]", "", text)  # strip markdown
        self._queue.put(clean)

    def stop(self) -> None:
        """Interrupt current speech and flush the queue."""
        self._stop_evt.set()

        # Drain queue without blocking
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

        # Stop pygame channel
        if self._channel and pygame.mixer.get_init():
            try:
                self._channel.stop()
            except Exception:
                pass

        # Kill PowerShell process if running
        if self._current_ps_process:
            try:
                self._current_ps_process.kill()
            except Exception:
                pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Keep the asyncio loop running forever in its own thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _worker(self) -> None:
        while True:
            text = self._queue.get()
            if text is None:
                break

            self._stop_evt.clear()
            print(f"[TTS] Speaking: {text[:60]}{'...' if len(text) > 60 else ''}")

            try:
                self._speak_edge(text)
            except Exception as e:
                print(f"[TTS] edge-tts error: {e} — falling back to pyttsx3")
                try:
                    self._speak_pyttsx3(text)
                except Exception as py_err:
                    print(f"[TTS] pyttsx3 error: {py_err} — using PowerShell")
                    self._speak_powershell(text)

    def _setup_pyttsx(self, engine: pyttsx3.Engine) -> None:
        voices  = engine.getProperty("voices")
        rate    = config_manager.get("voice.rate", 170)
        volume  = config_manager.get("voice.volume", 1.0)

        selected = None
        for v in voices:
            if any(n in v.name for n in ("Kalpana", "Heera", "Uzma")):
                selected = v.id
                break
        if not selected:
            for v in voices:
                if any(n in v.name for n in ("Zira", "Hazel", "Female")):
                    selected = v.id
                    break
        if selected:
            engine.setProperty("voice", selected)
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)

    # ── edge-tts (primary) ────────────────────────────────────────────────────

    def _speak_edge(self, text: str) -> None:
        params, clean = _extract_emotion(text)
        buf_idx  = next(_buffer_cycle)
        tmp_path = _TEMP_FILES[buf_idx]

        async def _synthesise():
            comm = edge_tts.Communicate(
                text=clean,
                voice="ur-PK-UzmaNeural",
                rate=params["rate"],
                pitch=params["pitch"],
            )
            await comm.save(tmp_path)

        # Post to persistent loop — no new event loop created
        future = asyncio.run_coroutine_threadsafe(_synthesise(), self._loop)
        future.result(timeout=15)  # block worker thread until done

        if self._stop_evt.is_set():
            return

        if not self._channel or not pygame.mixer.get_init():
            raise RuntimeError("pygame mixer unavailable")

        sound = pygame.mixer.Sound(tmp_path)
        self._channel.play(sound)

        # Poll with stop-event awareness
        while self._channel.get_busy():
            if self._stop_evt.is_set():
                self._channel.stop()
                return
            pygame.time.wait(20)   # 20 ms polling — CPU-friendly

    # ── pyttsx3 (offline fallback) ────────────────────────────────────────────

    def _speak_pyttsx3(self, text: str) -> None:
        if not self.pyttsx_engine:
            raise RuntimeError("pyttsx3 not initialised")
        if self._stop_evt.is_set():
            return
        _, clean = _extract_emotion(text)
        self.pyttsx_engine.say(clean)
        self.pyttsx_engine.runAndWait()

    # ── PowerShell SAPI (last resort) ─────────────────────────────────────────

    def _speak_powershell(self, text: str) -> None:
        _, clean = _extract_emotion(text)

        # Split if too long
        if len(clean) > 1000:
            for s in re.split(r"(?<=[.!?]) +", clean):
                if s.strip():
                    self._speak_powershell(s)
            return

        safe = clean.replace("'", "''").replace("\n", " ").replace("\r", " ")
        rate = config_manager.get("voice.rate", 170)
        ps_rate = max(-10, min(10, int((rate - 170) / 10)))

        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"foreach ($v in $s.GetInstalledVoices()) {{ "
            f"  if ($v.VoiceInfo.Name -match 'Kalpana|Heera|Uzma') {{ $s.SelectVoice($v.VoiceInfo.Name); break }} }}; "
            f"$s.Rate = {ps_rate}; $s.Speak('{safe}')"
        ]
        try:
            self._current_ps_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._current_ps_process.wait(timeout=30)
        except Exception as e:
            print(f"[TTS] PowerShell error: {e}")
        finally:
            self._current_ps_process = None


# Global singleton
tts_engine = TTSEngine()
