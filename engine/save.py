import json
import os
from engine.player import Player

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".monster_tamer")
SAVE_PATH = os.path.join(SAVE_DIR, "save.json")


def save_game(player):
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(SAVE_PATH, 'w') as f:
        json.dump(player.to_dict(), f, indent=2)


def load_game():
    if not os.path.exists(SAVE_PATH):
        return None
    try:
        with open(SAVE_PATH) as f:
            data = json.load(f)
        return Player.from_dict(data)
    except Exception:
        return None


def has_save():
    return os.path.exists(SAVE_PATH)


def delete_save():
    if os.path.exists(SAVE_PATH):
        os.remove(SAVE_PATH)
