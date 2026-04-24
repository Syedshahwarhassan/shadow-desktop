import os
import time
import pyautogui
import pyperclip
import winshell
from pathlib import Path

class DesktopCommands:
    @staticmethod
    def screenshot():
        try:
            # Use winshell to get the actual Desktop path (handles OneDrive etc.)
            desktop = winshell.desktop()
            path = os.path.join(desktop, "screenshot.png")
            pyautogui.screenshot(path)
            return f"Screenshot saved to Desktop."
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")
            # Fallback to home dir
            try:
                path = os.path.join(os.path.expanduser("~"), "screenshot.png")
                pyautogui.screenshot(path)
                return "Desktop not found. Screenshot saved to your home folder."
            except:
                return "I couldn't save the screenshot."

    @staticmethod
    def empty_trash():
        try:
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=True)
            return "Recycle bin emptied."
        except:
            return "Failed to empty trash."

    @staticmethod
    def take_note(text):
        if not text:
            return "What should I write in the note?"
        
        # Save notes in the user's Documents folder for better visibility
        docs = winshell.folder("personal")
        notes_dir = os.path.join(docs, "Shadow_Notes")
        if not os.path.exists(notes_dir):
            os.makedirs(notes_dir)
        
        path = os.path.join(notes_dir, "notes.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
        return "Note saved in your Documents folder."

    @staticmethod
    def open_downloads():
        try:
            path = winshell.folder("downloads")
            os.startfile(path)
            return "Opening Downloads."
        except:
            # Fallback
            path = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.exists(path):
                os.startfile(path)
                return "Opening Downloads."
            return "I couldn't find your Downloads folder."
            
    @staticmethod
    def move_window(direction):
        return f"Moving window {direction}."
