import json
import os

class MemoryManager:
    def __init__(self, memory_file="memory.json"):
        self.memory_file = memory_file
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

memory_manager = MemoryManager()
