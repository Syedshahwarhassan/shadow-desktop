import threading
import queue
import subprocess
import os
import re
from config_manager import config_manager

class TTSEngine:
    """
    Highly robust TTS engine for Windows.
    Uses pyttsx3 as primary, but can be forced to use PowerShell (System.Speech)
    which is much more reliable on modern Windows 10/11 systems.
    """
    def __init__(self):
        self._queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def speak(self, text):
        if text:
            # Clean text for console and TTS (remove markdown, symbols)
            clean_text = re.sub(r'[*_`#]', '', text)
            clean_text = clean_text.replace("[", "").replace("]", "")
            self._queue.put(clean_text)

    def _worker(self):
        # Check config to see if we should force PowerShell
        force_ps = config_manager.get("voice.force_powershell", True) # Default to True for reliability
        
        engine = None
        if not force_ps:
            try:
                import pyttsx3
                import pythoncom
                pythoncom.CoInitialize()
                engine = pyttsx3.init()
                self._setup_pyttsx(engine)
                print("[TTS] pyttsx3 initialized.")
            except Exception as e:
                print(f"[TTS] pyttsx3 init failed: {e}. Falling back to PowerShell.")
                engine = None

        while True:
            text = self._queue.get()
            if text is None: break
            
            print(f"[TTS] Speaking: {text[:50]}...")
            
            if force_ps or engine is None:
                self._speak_powershell(text)
            else:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"[TTS] pyttsx3 error: {e}. Using PowerShell fallback.")
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
            f"$speak.Speak('{safe_text}')"
        ]
        
        try:
            # We use check=True to catch errors
            subprocess.run(command, 
                           creationflags=subprocess.CREATE_NO_WINDOW,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE,
                           text=True,
                           timeout=30)
        except Exception as e:
            print(f"[TTS] PowerShell Error: {e}")

# Global instance
tts_engine = TTSEngine()
