import json
import os

import config

def _build_path(multiplayer: bool) -> str:
    filename = "current_run_mp.save" if multiplayer else "current_run.save"
    return os.path.join(
        config._sts2_data_dir(), "steam", config.STEAM_ID, f"profile{config.PROFILE}", "saves", filename
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


def _run_history_path(run_id: str) -> str:
    return os.path.join(
        config._sts2_data_dir(), "steam", config.STEAM_ID, f"profile{config.PROFILE}", "saves", "history", f"{run_id}.run"
    )


def read_run_history(run_id: str) -> dict | None:
    try:
        with open(_run_history_path(run_id), "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except Exception:
        return None


def read_run_result(run_id: str) -> bool | None:
    data = read_run_history(run_id)
    return data.get("win") if data else None


def _our_pstat(map_point: dict) -> dict | None:
    our_pid = int(config.STEAM_ID)
    pstats = map_point.get("player_stats", [])
    match = next((p for p in pstats if p.get("player_id") == our_pid), None)
    if match is None and len(pstats) == 1:
        match = pstats[0]
    return match


def read_run_card_offers(run_id: str, data: dict | None = None) -> dict:
    """Returns {encounter_name: [[offer, ...], ...]} in visit order for our player.

    Each encounter name maps to a list of offer-lists (one per visit), so duplicate
    encounters in a single run can be matched positionally by the caller.
    Only covers combat-type rooms (monster, elite, boss) where card_choices = reward pool.
    """
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_history in data.get("map_point_history", []):
        for map_point in act_history:
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            room = rooms[0]
            if room.get("room_type") not in ("monster", "elite", "boss"):
                continue
            model_id = room.get("model_id", "")
            encounter = model_id.split(".", 1)[-1] if "." in model_id else None
            if not encounter:
                continue

            pstat = _our_pstat(map_point)
            if pstat is None:
                continue
            choices = [
                {
                    "id": c["card"]["id"].replace("CARD.", ""),
                    "was_picked": c.get("was_picked", False),
                }
                for c in pstat.get("card_choices", [])
                if "id" in c.get("card", {})
            ]
            if choices:
                result.setdefault(encounter, []).append(choices)

    return result


def read_run_potions_used(run_id: str, data: dict | None = None) -> dict:
    """Returns {encounter_name: [["POTION_ID", ...], ...]} in visit order for combat rooms."""
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_history in data.get("map_point_history", []):
        for map_point in act_history:
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            room = rooms[0]
            if room.get("room_type") not in ("monster", "elite", "boss"):
                continue
            model_id = room.get("model_id", "")
            encounter = model_id.split(".", 1)[-1] if "." in model_id else None
            if not encounter:
                continue

            pstat = _our_pstat(map_point)
            if pstat is None:
                continue
            potions = [p.replace("POTION.", "") for p in pstat.get("potion_used", [])]
            result.setdefault(encounter, []).append(potions)

    return result


def read_run_monster_ids(run_id: str, data: dict | None = None) -> dict:
    """Returns {encounter_name: [[monster_id, ...], ...]} in visit order for combat rooms."""
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_history in data.get("map_point_history", []):
        for map_point in act_history:
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            room = rooms[0]
            if room.get("room_type") not in ("monster", "elite", "boss"):
                continue
            model_id = room.get("model_id", "")
            encounter = model_id.split(".", 1)[-1] if "." in model_id else None
            if not encounter:
                continue
            monsters = [m.replace("MONSTER.", "") for m in room.get("monster_ids", [])]
            result.setdefault(encounter, []).append(monsters)

    return result


def read_run_cards_removed(run_id: str, data: dict | None = None) -> dict:
    """Returns {"by_encounter": {name: [[id,...],...]}, "by_act": {act: [[id,...],...]}}
    by_encounter covers ancient rooms (have model_id); by_act covers shop rooms.
    """
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {"by_encounter": {}, "by_act": {}}

    by_encounter: dict = {}
    by_act: dict = {}

    for act_idx, act_history in enumerate(data.get("map_point_history", [])):
        act = act_idx + 1
        for map_point in act_history:
            pstat = _our_pstat(map_point)
            if pstat is None:
                continue
            removed = [c["id"].replace("CARD.", "") for c in pstat.get("cards_removed", []) if "id" in c]
            if not removed:
                continue
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            model_id = rooms[0].get("model_id", "")
            if model_id:
                encounter = model_id.split(".", 1)[-1]
                by_encounter.setdefault(encounter, []).append(removed)
            else:
                by_act.setdefault(act, []).append(removed)

    return {"by_encounter": by_encounter, "by_act": by_act}


def read_run_gold_breakdown(run_id: str, data: dict | None = None) -> dict:
    """Returns {"by_encounter": {name: [gold_dict,...]}, "by_act": {(act, mp_type): [gold_dict,...]}}
    Rooms with model_id go in by_encounter; shop/rest_site/treasure go in by_act.
    gold_dict keys: gained, spent, lost, stolen.
    """
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {"by_encounter": {}, "by_act": {}}

    by_encounter: dict = {}
    by_act: dict = {}

    for act_idx, act_history in enumerate(data.get("map_point_history", [])):
        act = act_idx + 1
        for map_point in act_history:
            pstat = _our_pstat(map_point)
            if pstat is None:
                continue
            gold = {
                "gained": pstat.get("gold_gained", 0),
                "spent": pstat.get("gold_spent", 0),
                "lost": pstat.get("gold_lost", 0),
                "stolen": pstat.get("gold_stolen", 0),
            }
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            model_id = rooms[0].get("model_id", "")
            if model_id:
                encounter = model_id.split(".", 1)[-1]
                by_encounter.setdefault(encounter, []).append(gold)
            else:
                key = (act, map_point.get("map_point_type"))
                by_act.setdefault(key, []).append(gold)

    return {"by_encounter": by_encounter, "by_act": by_act}


def read_run_turns_taken(run_id: str, data: dict | None = None) -> dict:
    """Returns {encounter_name: [turns, ...]} in visit order for combat rooms."""
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_history in data.get("map_point_history", []):
        for map_point in act_history:
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            room = rooms[0]
            if room.get("room_type") not in ("monster", "elite", "boss"):
                continue
            model_id = room.get("model_id", "")
            encounter = model_id.split(".", 1)[-1] if "." in model_id else None
            if not encounter:
                continue
            turns = room.get("turns_taken")
            if turns is not None:
                result.setdefault(encounter, []).append(turns)

    return result


def read_run_rest_choices(run_id: str, data: dict | None = None) -> dict:
    """Returns {act: [{"choice": str, "upgraded_cards": [...]}, ...]} in visit order."""
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_idx, act_history in enumerate(data.get("map_point_history", [])):
        act = act_idx + 1
        for map_point in act_history:
            if map_point.get("map_point_type") != "rest_site":
                continue

            pstat = _our_pstat(map_point)
            if pstat is None:
                continue

            choices = pstat.get("rest_site_choices", [])
            upgraded = [c.replace("CARD.", "") for c in pstat.get("upgraded_cards", [])]
            result.setdefault(act, []).append({
                "choice": choices[0] if choices else None,
                "upgraded_cards": upgraded,
            })

    return result


def read_run_event_choices(run_id: str, data: dict | None = None) -> dict:
    """Returns {encounter_name: [[{key, table}, ...], ...]} in visit order for event rooms."""
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_history in data.get("map_point_history", []):
        for map_point in act_history:
            if map_point.get("map_point_type") != "unknown":
                continue
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            model_id = rooms[0].get("model_id", "")
            encounter = model_id.split(".", 1)[-1] if "." in model_id else None
            if not encounter:
                continue

            pstat = _our_pstat(map_point)
            if pstat is None:
                continue
            choices = [
                {"key": c["title"]["key"], "table": c["title"].get("table")}
                for c in pstat.get("event_choices", [])
                if "title" in c and "key" in c["title"]
            ]
            if choices:
                result.setdefault(encounter, []).append(choices)

    return result


def read_run_ancient_choices(run_id: str, data: dict | None = None) -> dict:
    """Returns {encounter_name: [[{id, was_chosen}, ...], ...]} in visit order for our player."""
    if data is None:
        data = read_run_history(run_id)
    if not data:
        return {}

    result = {}

    for act_history in data.get("map_point_history", []):
        for map_point in act_history:
            if map_point.get("map_point_type") != "ancient":
                continue
            rooms = map_point.get("rooms", [])
            if not rooms:
                continue
            model_id = rooms[0].get("model_id", "")
            encounter = model_id.split(".", 1)[-1] if "." in model_id else None
            if not encounter:
                continue

            pstat = _our_pstat(map_point)
            if pstat is None:
                continue
            choices = [
                {"id": c["TextKey"], "was_chosen": c.get("was_chosen", False)}
                for c in pstat.get("ancient_choice", [])
                if "TextKey" in c
            ]
            if choices:
                result.setdefault(encounter, []).append(choices)

    return result


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
