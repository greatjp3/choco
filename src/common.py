from pathlib import Path

import json


SOURCE_DIR = Path(__file__).parent
log_file_path = SOURCE_DIR / "log/events.log"

def load_settings():
    settings_path = SOURCE_DIR / "settings.json"
    with open(settings_path, "r") as f:
        settings = json.load(f)
        return settings