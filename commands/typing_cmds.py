"""
typing_cmds.py — Voice-to-text typing commands.

Features:
  - "Shadow, type [text]"         → types the spoken text at cursor position
  - "Shadow, dictation on"        → enters dictation mode (everything typed automatically)
  - "Shadow, dictation off/stop"  → exits dictation mode
  - "Shadow, press enter"         → presses Enter key
  - "Shadow, press backspace"     → presses Backspace
  - "Shadow, press tab"           → presses Tab
  - "Shadow, select all"          → Ctrl+A
  - "Shadow, copy"                → Ctrl+C
  - "Shadow, paste"               → Ctrl+V
  - "Shadow, undo"                → Ctrl+Z
  - "Shadow, new line"            → presses Enter

Urdu equivalents:
  - "Shadow, type karo [text]"
  - "Shadow, likhna shuru karo"   → dictation on
  - "Shadow, likhna band karo"    → dictation off
"""

import time
import pyperclip
import pyautogui

# Disable pyautogui failsafe (moving mouse to corner won't abort)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.03  # small delay between key actions


class TypingCommands:

    @staticmethod
    def type_text(text: str) -> str:
        """
        Type text at the current cursor position.
        Uses clipboard (copy+paste) for full Unicode support including Urdu.
        """
        if not text or not text.strip():
            return "Nothing to type."

        try:
            # Save old clipboard content
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = ""

            # Set new text to clipboard and paste
            pyperclip.copy(text)
            time.sleep(0.15)  # let clipboard update
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)

            # Restore old clipboard
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass

            print(f"[TYPE] Typed: {text}")
            return f"Typed: {text}"

        except Exception as e:
            print(f"[TYPE] Error: {e}")
            return f"Could not type text. Error: {str(e)}"

    @staticmethod
    def press_key(key: str) -> str:
        """Press a named keyboard key."""
        key_map = {
            "enter":      "enter",
            "backspace":  "backspace",
            "delete":     "delete",
            "tab":        "tab",
            "escape":     "escape",
            "space":      "space",
            "up":         "up",
            "down":       "down",
            "left":       "left",
            "right":      "right",
            "home":       "home",
            "end":        "end",
            "page up":    "pageup",
            "page down":  "pagedown",
        }
        actual_key = key_map.get(key.lower(), key.lower())
        try:
            pyautogui.press(actual_key)
            return f"Pressed {key}."
        except Exception as e:
            return f"Could not press {key}: {str(e)}"

    @staticmethod
    def keyboard_shortcut(action: str) -> str:
        """Execute a common keyboard shortcut."""
        shortcut_map = {
            "select all":   ("ctrl", "a"),
            "copy":         ("ctrl", "c"),
            "paste":        ("ctrl", "v"),
            "cut":          ("ctrl", "x"),
            "undo":         ("ctrl", "z"),
            "redo":         ("ctrl", "y"),
            "save":         ("ctrl", "s"),
            "find":         ("ctrl", "f"),
            "new tab":      ("ctrl", "t"),
            "close tab":    ("ctrl", "w"),
            "new window":   ("ctrl", "n"),
            "bold":         ("ctrl", "b"),
            "italic":       ("ctrl", "i"),
            "underline":    ("ctrl", "u"),
            "refresh":      ("f5",),
            "full screen":  ("f11",),
        }
        keys = shortcut_map.get(action.lower())
        if keys:
            try:
                pyautogui.hotkey(*keys)
                return f"{action} done."
            except Exception as e:
                return f"Could not execute {action}: {str(e)}"
        return f"Unknown shortcut: {action}"


class DictationMode:
    """
    Singleton that tracks whether dictation mode is active.
    When active, the listener will type everything it hears (after wake word).
    """
    _active = False

    @classmethod
    def turn_on(cls) -> str:
        cls._active = True
        print("[DICTATION] Mode ON")
        return "Dictation mode on. Everything you say will be typed. Say 'dictation off' to stop."

    @classmethod
    def turn_off(cls) -> str:
        cls._active = False
        print("[DICTATION] Mode OFF")
        return "Dictation mode off."

    @classmethod
    def is_active(cls) -> bool:
        return cls._active

    @classmethod
    def handle(cls, text: str) -> str:
        """Type the spoken text if dictation mode is active."""
        return TypingCommands.type_text(text)
