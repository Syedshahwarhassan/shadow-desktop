import threading
import queue
import subprocess
import os
import re
import asyncio
import edge_tts
import pyttsx3
from config_manager import config_manager

class TTSEngine:
    """
    Highly robust TTS engine for Windows.
    Uses pyttsx3 as primary, but can be forced to use PowerShell (System.Speech)
    which is much more reliable on modern Windows 10/11 systems.
    """
    def __init__(self):
        self._queue = queue.Queue()
        self._current_ps_process = None
        self._stop_flag = False
        
        # Initialize pyttsx3
        try:
            self.pyttsx_engine = pyttsx3.init()
            self._setup_pyttsx(self.pyttsx_engine)
        except Exception as e:
            print(f"[TTS] Failed to initialize pyttsx3: {e}")
            self.pyttsx_engine = None
            
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def speak(self, text):
        if text:
            # Clean text for console and TTS (remove markdown, symbols)
            # Preserve square brackets for emotion detection
            clean_text = re.sub(r'[*_`#]', '', text)
            self._queue.put(clean_text)

    def _extract_emotion(self, text):
        """
        Extracts emotion tag and returns (params, clean_text).
        Parameters include pitch and rate for edge-tts.
        """
        emotions = {
            "[HAPPY]":   {"pitch": "+15Hz", "rate": "-5%"},
            "[EXCITED]": {"pitch": "+25Hz", "rate": "+5%"},
            "[SAD]":     {"pitch": "-15Hz", "rate": "-25%"},
            "[ANGRY]":   {"pitch": "-5Hz",  "rate": "+10%"},
            "[CURIOUS]": {"pitch": "+10Hz", "rate": "-10%"},
            "[CALM]":    {"pitch": "+0Hz",  "rate": "-15%"},
        }
        
        for tag, params in emotions.items():
            if text.startswith(tag):
                return params, text[len(tag):].strip()
        
        # Fallback/Heuristics if no explicit tag
        pitch = "+0Hz"
        rate = "-10%"
        
        if "!" in text or any(w in text.lower() for w in ["واہ", "زبردست", "ہاہا", "ارے"]):
            pitch = "+15Hz"
            rate = "-5%"
        elif "?" in text:
            pitch = "+5Hz"
        elif any(w in text.lower() for w in ["افسوس", "سوری", "sad"]):
            pitch = "-15Hz"
            rate = "-20%"
            
        return {"pitch": pitch, "rate": rate}, text

    def stop(self):
        """Immediately stops speech and clears the queue."""
        self._stop_flag = True
        
        # Clear the queue
        with self._queue.mutex:
            self._queue.queue.clear()
        
        # Terminate any running PowerShell process
        if self._current_ps_process:
            try:
                self._current_ps_process.kill()
            except:
                pass

        # Stop pygame audio if it's playing
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except:
            pass


    def _worker(self):
        while True:
            text = self._queue.get()
            if text is None: break
            
            self._stop_flag = False
            
            print(f"[TTS] Speaking: {text[:50]}...")
            
            try:
                self._speak_edge(text)
            except Exception as e:
                print(f"[TTS] edge-tts error: {e}. Falling back to pyttsx3.")
                try:
                    self._speak_pyttsx3(text)
                except Exception as py_err:
                    print(f"[TTS] pyttsx3 error: {py_err}. Using PowerShell fallback.")
                    self._speak_powershell(text)

    def _setup_pyttsx(self, engine):
        voices = engine.getProperty('voices')
        rate = config_manager.get("voice.rate", 170)
        volume = config_manager.get("voice.volume", 1.0)
        
        # Priority: Kalpana/Heera/Uzma > Zira/Hazel > Any female
        selected_voice = None
        for voice in voices:
            if "Kalpana" in voice.name or "Heera" in voice.name or "Uzma" in voice.name:
                selected_voice = voice.id
                break
        
        if not selected_voice:
            for voice in voices:
                if "Zira" in voice.name or "Hazel" in voice.name or "Female" in voice.name:
                    selected_voice = voice.id
                    break
                    
        if selected_voice:
            engine.setProperty('voice', selected_voice)
        
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)

    def _speak_pyttsx3(self, text):
        """Offline fallback using pyttsx3."""
        if not self.pyttsx_engine:
            raise Exception("pyttsx3 engine not initialized")
            
        if self._stop_flag:
            return

        # Strip emotion tags for pyttsx3
        _, clean_text = self._extract_emotion(text)
        
        self.pyttsx_engine.say(clean_text)
        self.pyttsx_engine.runAndWait()

    def _speak_edge(self, text):
        async def run():
            # Get emotion parameters and clean text
            params, clean_text = self._extract_emotion(text)
            
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice="ur-PK-UzmaNeural",
                rate=params["rate"],
                pitch=params["pitch"]
            )
            await communicate.save("temp.mp3")

        asyncio.run(run())

        if self._stop_flag:
            return

        # play audio
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load("temp.mp3")
        pygame.mixer.music.play()
        
        # Wait for the audio to finish playing, otherwise the TTS engine 
        # will immediately overwrite temp.mp3 for the next sentence
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # Unload to free the file handle so edge-tts can overwrite it next time
        pygame.mixer.music.unload()

    def _speak_powershell(self, text):
        """
        Directly calls Windows Speech API via PowerShell.
        Handles long text and special characters safely.
        """
        # Clean text for PowerShell (escape single quotes, remove newlines)
        safe_text = text.replace("'", "''").replace("\n", " ").replace("\r", " ")
        
        # Limit text length to avoid shell errors, split into sentences if too long
        if len(safe_text) > 1000:
            print("[TTS] Text too long, splitting...")
            sentences = re.split(r'(?<=[.!?]) +', safe_text)
            for s in sentences:
                if s.strip(): self._speak_powershell(s)
            return

        rate = config_manager.get("voice.rate", 170)
        ps_rate = int((rate - 170) / 10)
        ps_rate = max(-10, min(10, ps_rate))
        
        # Strip emotion tags for PowerShell
        _, clean_text_ps = self._extract_emotion(text)
        safe_text_ps = clean_text_ps.replace("'", "''").replace("\n", " ").replace("\r", " ")

        # Build PS command with NoProfile for speed
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$voices = $speak.GetInstalledVoices(); "
            f"$vName = ''; "
            f"foreach ($v in $voices) {{ if ($v.VoiceInfo.Name -match 'Kalpana|Heera|Uzma') {{ $vName = $v.VoiceInfo.Name; break; }} }}; "
            f"if ($vName -ne '') {{ $speak.SelectVoice($vName) }} else {{ try {{ $speak.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) }} catch {{}} }}; "
            f"$speak.Rate = {ps_rate}; "
            f"$speak.Speak('{safe_text_ps}')"
        ]
        
        try:
            # Use Popen so we can kill the process if interrupted
            self._current_ps_process = subprocess.Popen(
                command, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            self._current_ps_process.wait(timeout=30)
        except Exception as e:
            print(f"[TTS] PowerShell Error: {e}")
        finally:
            self._current_ps_process = None

# Global instance
tts_engine = TTSEngine()
