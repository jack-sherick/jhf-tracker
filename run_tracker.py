import re

import config
import db
from logtypes import CardPlayed, PotionUsed, MonsterPlayed, Encounter, CombatReward, RarityStats

_run: dict | None = None
_result: bool = True
_rt_act = 0
_rt_floor = 0
_prev_floor_health: int | None = None
_last_health: int | None = None


def _get_floor(act: int, floor: int) -> dict:
    key = f"{act}-{floor}"
    if key not in _run["floors"]:
        _run["floors"][key] = {
            "act": act,
            "floor": floor,
            "encounter": None,
            "mode": None,
            "cards_played": [],
            "potions_used": [],
            "monster_moves": [],
            "rarity_stats": None,
            "reward": None,
        }
    return _run["floors"][key]


def _add_event(act: int, floor: int, event):
    f = _get_floor(act, floor)

    if isinstance(event, Encounter):
        f["encounter"] = event.encounter
        f["mode"] = event.mode
    elif isinstance(event, CardPlayed):
        f["cards_played"].append({"card": event.card, "target": event.target, "turn": event.turn})
    elif isinstance(event, PotionUsed):
        f["potions_used"].append({"potion": event.potion, "target": event.target, "turn": event.turn})
    elif isinstance(event, MonsterPlayed):
        f["monster_moves"].append({"monster": event.monster, "move": event.move, "turn": event.turn})
    elif isinstance(event, RarityStats):
        f["rarity_stats"] = {
            "a": [event.a_rarity, event.a_offset],
            "b": [event.b_rarity, event.b_offset],
            "c": [event.c_rarity, event.c_offset],
        }
    elif isinstance(event, CombatReward):
        f["reward"] = {
            "gold": event.gold,
            "card": event.card,
            "potion": event.potion,
            "relic": event.relic,
        }


def on_save(snapshot: dict | None):
    global _prev_floor_health, _last_health

    if _run is None or snapshot is None:
        return

    if _prev_floor_health is None:
        # First save of the run — at the Ancient, before any combat
        _prev_floor_health = snapshot["health"]
        health_lost = 0
    else:
        health_lost = max(0, _prev_floor_health - snapshot["health"])

    _last_health = snapshot["health"]

    f = _get_floor(_rt_act, _rt_floor)
    f["health"] = snapshot["health"]
    f["max_health"] = snapshot["max_health"]
    f["health_lost"] = health_lost

    _run["gold"] = snapshot["gold"]
    _run["deck"] = snapshot["deck"]
    _run["health"] = snapshot["health"]
    _run["max_health"] = snapshot["max_health"]


def process(raw: str, events: list):
    global _run, _result, _rt_act, _rt_floor

    raw = raw.strip()

    # Run start
    m = re.search(r'Embarking on a singleplayer (\S+) run\. Ascension: (\d+) Seed: (\S+)', raw)
    if m:
        _run = {
            "run_id": None,
            "player_id": config.PLAYER_ID,
            "character": m.group(1),
            "ascension": int(m.group(2)),
            "seed": m.group(3),
            "result": None,
            "floor_reached": 0,
            "gold": 0,
            "health": None,
            "max_health": None,
            "deck": [],
            "floors": {},
        }
        _result = True
        _rt_act = 0
        _rt_floor = 0
        _prev_floor_health = None
        _last_health = None
        print(f"[run_tracker] Started: {m.group(1)} A{m.group(2)} seed={m.group(3)}")
        return

    if _run is None:
        return

    # Track loss
    if "has lost to encounter" in raw:
        _result = False

    # Add events to CURRENT floor first — CombatReward belongs to the floor
    # we're leaving, which is still _rt_act/_rt_floor at this point
    for event in events:
        _add_event(_rt_act, _rt_floor, event)

    # Then update floor from MapVote so subsequent events land on the new floor
    if "->MapVote" in raw:
        m = re.search(r'gen: (\d+) coord: \(\d+, (\d+)\)', raw)
        if m:
            _rt_act = int(m.group(1))
            _rt_floor = int(m.group(2))
            _run["floor_reached"] = max(_run["floor_reached"], _rt_floor)
            if _last_health is not None:
                _prev_floor_health = _last_health

    # Run end — write JSON
    m = re.search(r'Saved run history: (\S+)\.run', raw)
    if m:
        _run["run_id"] = m.group(1)
        _run["result"] = _result
        db.insert_run(_run)
        _run = None
        _result = True
