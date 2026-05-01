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
            return "سکرین شاٹ ڈیسک ٹاپ پر محفوظ کر دیا گیا ہے۔"
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")
            # Fallback to home dir
            try:
                path = os.path.join(os.path.expanduser("~"), "screenshot.png")
                pyautogui.screenshot(path)
                return "Desktop not found. Screenshot saved to your home folder."
            except:
                return "معذرت، سکرین شاٹ محفوظ نہیں ہو سکا۔"

    @staticmethod
    def empty_trash():
        try:
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=True)
            return "رئی سائیکل بن خالی کر دیا گیا ہے۔"
        except:
            return "معذرت، رئی سائیکل بن خالی نہیں ہو سکا۔"

    @staticmethod
    def take_note(text):
        if not text:
            return "نوٹ میں کیا لکھنا ہے؟"
        
        # Save notes in the user's Documents folder for better visibility
        docs = winshell.folder("personal")
        notes_dir = os.path.join(docs, "Shadow_Notes")
        if not os.path.exists(notes_dir):
            os.makedirs(notes_dir)
        
        path = os.path.join(notes_dir, "notes.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
        return "نوٹ آپ کے ڈاکومنٹس فولڈر میں محفوظ کر دیا گیا ہے۔"

    @staticmethod
    def open_downloads():
        try:
            path = winshell.folder("downloads")
            os.startfile(path)
            return "ڈاؤن لوڈز فولڈر کھول رہا ہوں۔"
        except:
            # Fallback
            path = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.exists(path):
                os.startfile(path)
                return "ڈاؤن لوڈز فولڈر کھول رہا ہوں۔"
            return "معذرت، مجھے آپ کا ڈاؤن لوڈز فولڈر نہیں ملا۔"
            
    @staticmethod
    def move_window(direction):
        return f"Moving window {direction}."

    @staticmethod
    def create_folder(name):
        if not name:
            return "فولڈر کا نام کیا رکھنا ہے؟"
        try:
            desktop = winshell.desktop()
            path = os.path.join(desktop, name)
            os.makedirs(path, exist_ok=True)
            print(f"[CMD] Created folder at: {path}")
            return f"ڈیسک ٹاپ پر '{name}' کے نام کا فولڈر بنا دیا گیا ہے۔"
        except Exception as e:
            print(f"[ERROR] Create folder failed: {e}")
            return f"معذرت، میں '{name}' کے نام کا فولڈر نہیں بنا سکا۔"

    @staticmethod
    def create_file(name):
        if not name:
            return "فائل کا نام کیا رکھنا ہے؟"
        try:
            desktop = winshell.desktop()
            # If no extension is provided, default to .txt
            if "." not in name:
                name += ".txt"
            path = os.path.join(desktop, name)
            with open(path, "w", encoding="utf-8") as f:
                pass # Create empty file
            print(f"[CMD] Created file at: {path}")
            return f"ڈیسک ٹاپ پر '{name}' کے نام کی فائل بنا دی گئی ہے۔"
        except Exception as e:
            print(f"[ERROR] Create file failed: {e}")
            return f"معذرت، میں '{name}' کے نام کی فائل نہیں بنا سکا۔"
