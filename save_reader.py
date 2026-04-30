import json
import os

import config

SAVE_PATH = os.path.expandvars(
    rf"%APPDATA%\SlaytheSpire2\steam\{config.STEAM_ID}\profile{config.PROFILE}\saves"
    rf"\{'current_run.save' if config.SINGLEPLAYER else 'current_run_mp.save'}"
)

def read_save() -> str:
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def parse_save(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        player = data["players"][0]
        return {
            "character": player["character_id"],
            "health": player["current_hp"],
            "max_health": player["max_hp"],
            "gold": player["gold"],
            "deck": player["deck"],
        }
    except Exception:
        return None
