"""
messaging.py — Voice-controlled WhatsApp and messaging commands.

Supported voice patterns (English + Urdu):
  "Shadow, send WhatsApp to Ahmed hello bhai"
  "Shadow, WhatsApp karo Ahmed ko hello"
  "Shadow, message Ahmed I am coming"
  "Shadow, Ahmed ko WhatsApp karo main aa raha hoon"
"""

import time
import webbrowser
import pyautogui
import urllib.parse
from config_manager import config_manager


class MessagingCommands:

    # ── WhatsApp ──────────────────────────────────────────────────────────────

    @staticmethod
    def send_whatsapp(contact_name: str, message: str) -> str:
        """
        Send a WhatsApp message using Windows Desktop App GUI automation.
        Opens WhatsApp, searches for the contact name, selects them, and sends the message.
        """
        import os
        print(f"[WHATSAPP] Opening WhatsApp to send to {contact_name}...")

        try:
            # 1. Open WhatsApp Windows App
            os.system('start whatsapp:')
            
            # 2. Wait for it to open and focus
            time.sleep(3.0)
            
            # 3. Press Ctrl+F to focus the search bar
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(1.0)
            
            # Clear any existing text in the search bar
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.5)
            
            # 4. Type the contact name
            pyautogui.write(contact_name)
            time.sleep(1.5) # Wait for search results
            
            # 5. Press Down Arrow then Enter to select the top result
            pyautogui.press('down')
            time.sleep(0.5)
            pyautogui.press('enter')
            
            # 6. Wait for chat to open
            time.sleep(1.0)
            
            # 7. Type the message
            pyautogui.write(message)
            time.sleep(0.5)
            
            # 8. Press Enter to send
            pyautogui.press('enter')
            
            return f"{contact_name} ko WhatsApp message bhej diya gaya hai: '{message}'"

        except Exception as e:
            print(f"[WHATSAPP] Error: {e}")
            return f"{contact_name} ko message bhejte hue masla aagaya. Error: {str(e)}"

    @staticmethod
    def parse_whatsapp_command(text: str):
        """
        Parse voice text into (contact_name, message).
        Handles both English and Urdu patterns.
        Returns (contact, message) or (None, None) if parsing fails.
        """
        import re

        text = text.lower().strip()

        # ── English patterns ──────────────────────────────────────────────────
        # "send whatsapp to Ahmed hello"
        # "whatsapp Ahmed hello how are you"
        # "message Ahmed I am coming"
        # "send message to Ahmed I am coming"

        patterns_en = [
            r"send\s+whatsapp\s+(?:to\s+)?(\w+)\s+(.+)",
            r"whatsapp\s+(\w+)\s+(.+)",
            r"send\s+message\s+(?:to\s+)?(\w+)\s+(.+)",
            r"message\s+(\w+)\s+(.+)",
            r"text\s+(\w+)\s+(.+)",
        ]

        # ── Urdu patterns (romanized and Arabic script) ────────────────────────
        # "Ahmed ko WhatsApp karo hello bhai"
        # "ماما کو واٹس ایپ کرو میں آ رہا ہوں"

        patterns_ur = [
            r"(\w+)\s+ko\s+whatsapp\s+(?:par\s+|per\s+)?(?:message\s+)?(?:karo\s+|bhejo\s+)?(.+)",
            r"whatsapp\s+(?:par\s+|per\s+)?(?:message\s+)?(?:karo\s+|bhejo\s+)?(\w+)\s+ko\s+(.+)",
            r"(\w+)\s+ko\s+message\s+(?:karo\s+|bhejo\s+)?(.+)",
            r"message\s+(?:karo\s+|bhejo\s+)?(\w+)\s+ko\s+(.+)",
            r"([\w\u0600-\u06FF]+)\s+کو\s+واٹس ایپ\s+(?:کرو\s+|بھیجو\s+)?(.+)",
            r"واٹس ایپ\s+(?:کرو\s+|بھیجو\s+)?([\w\u0600-\u06FF]+)\s+کو\s+(.+)",
            r"([\w\u0600-\u06FF]+)\s+کو\s+میسج\s+(?:کرو\s+|بھیجو\s+)?(.+)",
            r"میسج\s+(?:کرو\s+|بھیجو\s+)?([\w\u0600-\u06FF]+)\s+کو\s+(.+)",
        ]

        # Evaluate Urdu patterns first since they are more specific (e.g., contains 'ko', 'karo')
        # This prevents generic English patterns from matching parts of an Urdu sentence.
        for pattern in patterns_ur + patterns_en:
            match = re.search(pattern, text)
            if match:
                contact = match.group(1).strip()
                message = match.group(2).strip()
                # Skip if contact is a filler word
                if contact not in ["a", "the", "to", "ko", "ki", "ka"]:
                    return contact, message

        return None, None

    @staticmethod
    def add_contact(name: str, phone: str) -> str:
        """Add a contact to config.json contacts list."""
        contacts = config_manager.get("contacts", {})
        contacts[name.lower()] = phone
        config_manager.set("contacts", contacts)
        print(f"[CONTACTS] Added: {name} → {phone}")
        return f"Contact {name} added with number {phone}."

    @staticmethod
    def list_contacts() -> str:
        """List all saved contacts."""
        contacts = config_manager.get("contacts", {})
        if not contacts:
            return "No contacts saved. Add them to config.json under contacts."
        names = ", ".join(contacts.keys())
        return f"Your saved contacts are: {names}."
