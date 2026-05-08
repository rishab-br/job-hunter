import json
from pathlib import Path

_PROFILE_PATH = Path("user_data/profile.json")
_EXAMPLE_PATH = Path("user_data/profile.example.json")


def load() -> dict:
    path = _PROFILE_PATH if _PROFILE_PATH.exists() else _EXAMPLE_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def exists() -> bool:
    return _PROFILE_PATH.exists()
