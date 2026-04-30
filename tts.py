"""
tts.py — High-performance, pipelined TTS engine for Shadow Voice Assistant.

Architecture
────────────
• Two-stage Pipeline:
  1. Synthesis Worker: Takes text from _synth_queue, generates audio via edge-tts/pyttsx3.
  2. Playback Worker: Takes audio buffers from _play_queue and plays them via pygame.
• Background Synthesis: Synthesis of sentence N+1 happens while sentence N is playing.
• In-Memory Processing: Uses io.BytesIO for audio buffers (no disk I/O hits).
• Asyncio Integration: Persistent loop in daemon thread for edge_tts.
"""

import threading
import queue
import subprocess
import os
import re
import asyncio
import io
import time
import edge_tts
import pyttsx3
import pygame
from config_manager import config_manager

# ── Emotion map ───────────────────────────────────────────────────────────────
_EMOTION_MAP: dict[str, dict[str, str]] = {
    "[HAPPY]":   {"pitch": "+5Hz", "rate": "+0%"},
    "[EXCITED]": {"pitch": "+10Hz", "rate": "+5%"},
    "[SAD]":     {"pitch": "-8Hz", "rate": "-15%"},
    "[ANGRY]":   {"pitch": "-2Hz",  "rate": "+8%"},
    "[CURIOUS]": {"pitch": "+4Hz", "rate": "-5%"},
    "[CALM]":    {"pitch": "+0Hz",  "rate": "-10%"},
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


# ── Single temp file — TTS worker is single-threaded, no race condition
_TEMP_FILE = "temp.mp3"


class TTSEngine:
    """
    Pipelined TTS engine with decoupled synthesis and playback.
    """

    def __init__(self):
        self._synth_queue: queue.Queue[str | None] = queue.Queue()
        self._play_queue:  queue.Queue[pygame.mixer.Sound | None] = queue.Queue()
        self._stop_evt     = threading.Event()
        self._current_ps_process: subprocess.Popen | None = None
        self.is_speaking: bool = False
        self.is_muted: bool = False

        # ── pygame mixer (initialised once) ───────────────────────────────────
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
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

        # ── Asyncio loop for edge-tts ─────────────────────────────────────────
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True, name="tts-loop").start()

        # ── Pipeline Workers ──────────────────────────────────────────────────
        threading.Thread(target=self._synthesis_worker, daemon=True, name="tts-synth").start()
        threading.Thread(target=self._playback_worker, daemon=True, name="tts-play").start()

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        if not text or self.is_muted: return
        clean = re.sub(r"[*_`#]", "", text)
        # Split long texts into sentences to enable pipelining immediately
        # Increased threshold to 250 to keep natural phrasing together
        if len(clean) > 250:
            sentences = re.split(r'(?<=[.!?۔]) +', clean)
            for s in sentences:
                if s.strip(): self._synth_queue.put(s.strip())
        else:
            self._synth_queue.put(clean)

    def stop(self) -> None:
        """Immediate interrupt and flush."""
        self._stop_evt.set()
        self.is_speaking = False

        # Flush both queues
        for q in (self._synth_queue, self._play_queue):
            try:
                while True: q.get_nowait()
            except queue.Empty: pass

        if self._channel and pygame.mixer.get_init():
            try: self._channel.stop()
            except Exception: pass

        if self._current_ps_process:
            try: self._current_ps_process.kill()
            except Exception: pass

    def set_muted(self, state: bool) -> None:
        """Set the mute state of the TTS engine."""
        self.is_muted = state
        if state:
            self.stop() # Stop any ongoing speech if muting

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Keep the asyncio loop running forever in its own thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _synthesis_worker(self) -> None:
        while True:
            text = self._synth_queue.get()
            if text is None: break

            self._stop_evt.clear()
            # Note: is_speaking is now managed by the playback worker
            
            try:
                t0 = time.perf_counter()
                audio_data = self._synthesize_edge(text)
                if audio_data:
                    sound = pygame.mixer.Sound(io.BytesIO(audio_data))
                    ms = (time.perf_counter() - t0) * 1000
                    print(f"[TTS] Synth complete: {ms:.0f}ms for '{text[:30]}...'")
                    self._play_queue.put(sound)
                else:
                    raise RuntimeError("Edge-TTS synthesis failed")

            except Exception as e:
                print(f"[TTS] Edge-TTS error: {e} — using fallback")
                # Fallbacks are sequential and block synth worker (rare case)
                try:
                    self._speak_pyttsx3(text)
                except Exception:
                    self._speak_powershell(text)

    def _playback_worker(self) -> None:
        while True:
            sound = self._play_queue.get()
            if sound is None: break

            if self._stop_evt.is_set(): continue

            self.is_speaking = True
            try:
                self._channel.play(sound)
                # Minimize polling delay for smoother transitions
                while self._channel.get_busy():
                    if self._stop_evt.is_set():
                        self._channel.stop()
                        break
                    time.sleep(0.001) 
            finally:
                if self._play_queue.empty():
                    self.is_speaking = False

    def _synthesize_edge(self, text: str) -> bytes | None:
        params, clean = _extract_emotion(text)
        
        async def _task():
            comm = edge_tts.Communicate(
                text=clean,
                voice="ur-PK-AsadNeural",
                rate=params["rate"],
                pitch=params["pitch"],
            )
            data = b""
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    data += chunk["data"]
            return data

        future = asyncio.run_coroutine_threadsafe(_task(), self._loop)
        try:
            return future.result(timeout=10)
        except Exception:
            return None

    def _setup_pyttsx(self, engine: pyttsx3.Engine) -> None:
        voices  = engine.getProperty("voices")
        rate    = config_manager.get("voice.rate", 170)
        volume  = config_manager.get("voice.volume", 1.0)

        selected = None
        for v in voices:
            if any(n in v.name for n in ("David", "Asad", "Guy", "Christopher")):
                selected = v.id
                break
        if not selected:
            for v in voices:
                if any(n in v.name for n in ("Male", "James", "Mark")):
                    selected = v.id
                    break
        if selected:
            engine.setProperty("voice", selected)
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)


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
            f"  if ($v.VoiceInfo.Name -match 'David|Asad|Guy|Christopher') {{ $s.SelectVoice($v.VoiceInfo.Name); break }} }}; "
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
