import json
import os
import difflib
import random

class MemoryManager:
    def __init__(self, memory_file="memory.json"):
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.memory_file = os.path.join(base_dir, memory_file)
        self.memory = self.load_memory()

    def load_memory(self):
        if not os.path.exists(self.memory_file):
            return {"notes": []}
        
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[MEMORY] Error loading memory: {e}")
            return {"notes": []}

    def save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[MEMORY] Error saving memory: {e}")

    def add_note(self, note):
        if note not in self.memory["notes"]:
            self.memory["notes"].append(note)
            self.save_memory()
            print(f"[MEMORY] Saved note: {note}")

    def get_notes_string(self):
        if not self.memory["notes"]:
            return "No specific memories or notes saved yet."
        
        return "You have the following memories and notes:\n- " + "\n- ".join(self.memory["notes"])

    def search(self, query, threshold=0.3):
        """Finds the most relevant note using keyword overlap and similarity."""
        best_match = None
        highest_score = 0
        
        # Normalize query
        query_norm = query.lower().strip()
        
        for note in self.memory["notes"]:
            note_lower = note.lower()
            # 1. Direct keyword/phrase match (highest priority)
            if query_norm in note_lower or note_lower in query_norm:
                # Bonus for exact or substantial substring matches
                score = 0.8 + (min(len(query_norm), len(note_lower)) / max(len(query_norm), len(note_lower)) * 0.2)
            else:
                # 2. Sequence similarity
                score = difflib.SequenceMatcher(None, query_norm, note_lower).ratio()
            
            if score > highest_score:
                highest_score = score
                best_match = note
        
        if highest_score >= threshold:
            return best_match, highest_score
        return None, 0

    def get_offline_response(self, query):
        """Returns a formatted response in Urdu based on local memory fallback."""
        match, score = self.search(query)
        
        if match:
            prefixes = [
                "Mujhe yeh yaad hai:",
                "Mere records ke mutabiq:",
                "Jahan tak mujhe maloom hai,"
            ]
            return f"[CALM] {random.choice(prefixes)} {match}."
        
        # Generic offline responses if no memory match
        fallbacks = [
            "Main abhi offline hoon, lekin main aapke local commands (jaise open app, volume control) handle kar sakti hoon.",
            "Internet na hone ki wajah se mera brain thoda slow hai, lekin main local tasks kar sakti hoon.",
            "Maaf kijiye, main abhi sirf wahi bata sakti hoon jo mujhe pehle se yaad hai. Kya main koi app kholun?",
            "Mera AI core connect nahi ho raha, lekin main aapki local madad ke liye tayyar hoon."
        ]
        return f"[CALM] {random.choice(fallbacks)}"

memory_manager = MemoryManager()
