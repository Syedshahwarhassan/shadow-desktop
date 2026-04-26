"""
config_manager.py — Configuration management for Shadow.

Optimisations / fixes
─────────────────────
• Explicit UTF-8 encoding on all file reads/writes — prevents Windows-1252
  decode errors on machines without UTF-8 as the system code page.
• reload() method allows runtime config refresh without restarting the app.
"""

import json
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


class ConfigManager:
    def __init__(self):
        self.config = self._load()

    def _load(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CONFIG] Load error: {e}")
            return {}

    def reload(self) -> None:
        """Reload config from disk at runtime."""
        self.config = self._load()
        print("[CONFIG] Reloaded from disk.")

    def save_config(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CONFIG] Save error: {e}")

    def get(self, key: str, default=None):
        keys = key.split(".")
        val  = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value) -> None:
        keys = key.split(".")
        val  = self.config
        for k in keys[:-1]:
            val = val.setdefault(k, {})
        val[keys[-1]] = value
        self.save_config()


config_manager = ConfigManager()
