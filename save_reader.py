import json
import os

import config

def _build_path(multiplayer: bool) -> str:
    filename = "current_run_mp.save" if multiplayer else "current_run.save"
    return os.path.expandvars(
        rf"%APPDATA%\SlaytheSpire2\steam\{config.STEAM_ID}\profile{config.PROFILE}\saves\{filename}"
    )

SAVE_PATH = _build_path(False)

def set_mode(multiplayer: bool):
    global SAVE_PATH
    SAVE_PATH = _build_path(multiplayer)

def detect_mode() -> bool:
    sp = _build_path(False)
    mp = _build_path(True)
    sp_t = os.path.getmtime(sp) if os.path.exists(sp) else 0
    mp_t = os.path.getmtime(mp) if os.path.exists(mp) else 0
    return mp_t > sp_t

def read_save() -> str:
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def get_current_event(raw: str, act: int) -> str | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        rooms = data["acts"][act - 1]["rooms"]
        idx = rooms["events_visited"]
        event_ids = rooms["event_ids"]
        if idx < len(event_ids):
            return event_ids[idx].replace("EVENT.", "")
        return None
    except Exception:
        print("[save_reader] bad event lookup")
        return None


def parse_save(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        players = data["players"]
        player = next(
            (p for p in players if str(p.get("net_id", "")) == config.STEAM_ID),
            players[0],
        )
        return {
            "character": player["character_id"],
            "health": player["current_hp"],
            "max_health": player["max_hp"],
            "gold": player["gold"],
            "deck": player["deck"],
            "relics": player.get("relics", []),
            "potions": player.get("potions", []),
        }
    except Exception:
        return None
