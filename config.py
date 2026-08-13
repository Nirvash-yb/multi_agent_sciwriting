import json
import os

_PATH = "config.json"

def load_config():
    if not os.path.exists(_PATH):
        return {}
    with open(_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()