import json
import os
import sys
import difflib
import random
import threading
import time

class MemoryManager:
    def __init__(self, memory_file: str = "memory.json"):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.memory_file = os.path.join(base_dir, memory_file)
        self.memory      = self._load()
        self._dirty      = False
        self._save_lock  = threading.Lock()

    def _load(self) -> dict:
        if not os.path.exists(self.memory_file):
            return {"notes": [], "_metadata": {}}
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "_metadata" not in data:
                    data["_metadata"] = {}
                return data
        except Exception as e:
            print(f"[MEMORY] Load error: {e}")
            return {"notes": [], "_metadata": {}}

    def save_memory(self, broadcast: bool = True) -> None:
        if not self._dirty:
            return
        self.memory["_metadata"]["notes"] = time.time()
        snapshot = json.dumps(self.memory, indent=4, ensure_ascii=False)
        def _write():
            with self._save_lock:
                try:
                    with open(self.memory_file, "w", encoding="utf-8") as f:
                        f.write(snapshot)
                    self._dirty = False
                except Exception as e:
                    print(f"[MEMORY] Save error: {e}")
        threading.Thread(target=_write, daemon=True, name="memory-save").start()


    def add_note(self, note: str) -> None:
        note = (note or "").strip()
        if not note or note in self.memory["notes"]:
            return
        self.memory["notes"].append(note)
        self._dirty = True
        self.save_memory()
        print(f"[MEMORY] Saved: {note}")

    def get_notes_string(self) -> str:
        if not self.memory["notes"]:
            return "No specific memories or notes saved yet."
        return "You have the following memories and notes:\n- " + \
               "\n- ".join(self.memory["notes"])

    def search(self, query: str) -> tuple:
        best, score = None, 0.0
        q = query.lower().strip()
        for note in self.memory["notes"]:
            n = note.lower()
            if q in n or n in q:
                s = 0.8 + min(len(q), len(n)) / max(len(q), len(n)) * 0.2
            else:
                s = difflib.SequenceMatcher(None, q, n).ratio()
            if s > score:
                score, best = s, note
        return (best, score) if score >= 0.6 else (None, 0)

    def get_offline_response(self, query: str) -> str:
        match, score = self.search(query)
        if match and score >= 0.6:
            prefix = random.choice([
                "Mujhe yeh yaad hai:", "Mere records ke mutabiq:",
                "Jahan tak mujhe maloom hai,"
            ])
            return f"[CALM] {prefix} {match}."
        fallbacks = [
            "Mera AI brain abhi connect nahi ho raha. Shayad API key ka masla hai ya internet slow hai.",
            "Main abhi offline hoon, isliye sirf local commands handle kar sakti hoon.",
            "Maaf kijiye, mujhe iska jawab nahi maloom aur mera brain connect nahi ho raha.",
            "Connection error ki wajah se main detail mein jawab nahi de sakti. Kya main koi app kholun?",
            "Mera AI core connect nahi ho raha, lekin main aapki local madad ke liye tayyar hoon."
        ]
        return f"[CALM] {random.choice(fallbacks)}"

memory_manager = MemoryManager()
