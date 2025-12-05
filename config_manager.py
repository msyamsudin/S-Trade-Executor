import json
import os
from typing import Dict, Any, List

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = {
            "actions": [],
            "always_on_top": True,
            "theme": "Dark"
        }
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_file):
            return self.default_config.copy()
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_actions(self) -> List[Dict[str, Any]]:
        """Get saved actions list."""
        # Support old profile format for backward compatibility
        if "profiles" in self.config:
            profiles = self.config.get("profiles", {})
            if profiles:
                first_profile = list(profiles.values())[0]
                return first_profile.get("actions", [])
        return self.config.get("actions", [])

    def save_actions(self, actions: List[Dict[str, Any]]):
        """Save actions list."""
        self.config["actions"] = actions
        # Remove old profile data if exists
        if "profiles" in self.config:
            del self.config["profiles"]
        if "last_profile" in self.config:
            del self.config["last_profile"]
        self.save_config()
