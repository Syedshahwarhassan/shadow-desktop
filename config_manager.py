import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        keys = key.split(".")
        val = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key, value):
        keys = key.split(".")
        val = self.config
        for k in keys[:-1]:
            if k not in val:
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value
        self.save_config()

config_manager = ConfigManager()
