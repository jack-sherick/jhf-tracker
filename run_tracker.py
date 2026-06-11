import re
from collections import Counter

import config
import db
import parser
import save_reader
from logtypes import CardPlayed, PotionUsed, MonsterPlayed, Encounter, CombatReward, RarityStats, MerchantAction

_run: dict | None = None
_result: bool = True
_rt_act = 0
_rt_floor = 0
_prev_floor_health: int | None = None
_prev_floor_max_health: int | None = None
_last_health: int | None = None
_last_max_health: int | None = None
_merchant_snapshot: dict | None = None
_patch: str | None = None


def set_patch(patch: str):
    global _patch
    _patch = patch
    print(f"[run_tracker] Game patch: {patch}")


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
            "rarity_stats": [],
            "reward": None,
            "cards_purchased": [],
            "relics_purchased": [],
            "potions_purchased": [],
            "card_cuts_purchased": [],
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
        f["rarity_stats"].append({
            "a": [event.a_rarity, event.a_offset],
            "b": [event.b_rarity, event.b_offset],
            "c": [event.c_rarity, event.c_offset],
        })
    elif isinstance(event, MerchantAction):
        f[event.action].extend(event.items)
    elif isinstance(event, CombatReward):
        f["reward"] = {
            "gold": event.gold,
            "card": event.card,
            "potion": event.potion,
            "relic": event.relic,
        }


def on_merchant_enter(snapshot: dict | None):
    global _merchant_snapshot
    _merchant_snapshot = snapshot


def _diff_merchant(before: dict, after: dict, floor: dict):
    def card_ids(deck): return [c["id"] for c in deck]

    before_cards = card_ids(before.get("deck", []))
    after_cards = card_ids(after.get("deck", []))

    # Cards added to deck = purchased
    for card in after_cards:
        if card in before_cards:
            before_cards.remove(card)
        else:
            floor["cards_purchased"].append(card.replace("CARD.", ""))

    # Relics added = purchased
    before_relics = {r["id"] for r in before.get("relics", [])}
    after_relics = {r["id"] for r in after.get("relics", [])}
    for relic in after_relics - before_relics:
        floor["relics_purchased"].append(relic.replace("RELIC.", ""))

    # Potions added = purchased (use Counter to handle duplicates)
    before_potions = Counter(p["id"] for p in before.get("potions", []))
    after_potions = Counter(p["id"] for p in after.get("potions", []))
    for potion_id, count in (after_potions - before_potions).items():
        for _ in range(count):
            floor["potions_purchased"].append(potion_id.replace("POTION.", ""))


def on_event_room(save_raw: str):
    import save_reader
    if _run is None:
        return
    event_name = save_reader.get_current_event(save_raw, _rt_act)
    f = _get_floor(_rt_act, _rt_floor)
    f["encounter"] = event_name
    f["mode"] = "Event"


def on_save(snapshot: dict | None):
    global _prev_floor_health, _prev_floor_max_health, _last_health, _last_max_health, _merchant_snapshot

    if _run is None or snapshot is None:
        return

    if _prev_floor_health is None:
        hp = snapshot["health"]
        if _run and _run.get("ascension", 0) >= 6:
            hp = round(hp * 0.8)
        _prev_floor_health = hp
        _prev_floor_max_health = snapshot["max_health"]
        health_lost = 0
        max_health_lost = 0
    else:
        health_lost = _prev_floor_health - snapshot["health"]
        max_health_lost = _prev_floor_max_health - snapshot["max_health"]

    _last_health = snapshot["health"]
    _last_max_health = snapshot["max_health"]

    f = _get_floor(_rt_act, _rt_floor)
    f["character"] = _run["character"]
    f["health"] = snapshot["health"]
    f["max_health"] = snapshot["max_health"]
    f["health_lost"] = health_lost
    f["max_health_lost"] = max_health_lost
    f["relics"] = snapshot.get("relics", [])
    f["floor_gold"] = snapshot["gold"]

    if _merchant_snapshot is not None:
        _diff_merchant(_merchant_snapshot, snapshot, f)
        _merchant_snapshot = snapshot  # roll forward so each diff is incremental

    _run["gold"] = snapshot["gold"]
    _run["deck"] = snapshot["deck"]
    _run["relics"] = snapshot.get("relics", [])
    _run["health"] = snapshot["health"]
    _run["max_health"] = snapshot["max_health"]


def _start_run(character: str, ascension: int, seed: str, multiplayer: bool):
    global _run, _result, _rt_act, _rt_floor, _prev_floor_health, _prev_floor_max_health, _last_health, _last_max_health, _merchant_snapshot
    _run = {
        "run_id": None,
        "player_id": config.PLAYER_ID,
        "character": character,
        "ascension": ascension,
        "seed": seed,
        "multiplayer": multiplayer,
        "patch": _patch,
        "result": None,
        "floor_reached": 0,
        "gold": 0,
        "health": None,
        "max_health": None,
        "deck": [],
        "relics": [],
        "floors": {},
    }
    _result = True
    _rt_act = 0
    _rt_floor = 0
    _prev_floor_health = None
    _prev_floor_max_health = None
    _last_health = None
    _last_max_health = None
    _merchant_snapshot = None
    mode = "multiplayer" if multiplayer else "singleplayer"
    print(f"[run_tracker] Started ({mode}): {character} A{ascension} seed={seed}")


def process(raw: str, events: list):
    global _run, _result, _rt_act, _rt_floor, _prev_floor_health, _prev_floor_max_health, _last_health, _last_max_health

    raw = raw.strip()

    # singleplayer run start
    m = re.search(r'Embarking on a singleplayer (\S+) run\. Ascension: (\d+) Seed: (\S+)', raw)
    if m:
        character, ascension, seed, multiplayer = m.group(1), int(m.group(2)), m.group(3), False
        parser.set_player_prefix("Player 1")
        save_reader.set_mode(False)
        _start_run(character, ascension, seed, multiplayer)
        return

    # multiplayer run start
    m = re.search(r'Embarking on a multiplayer run\. Players: (.+)\. Ascension: (\d+) Seed: (\S+)', raw)
    if m:
        players_str, ascension, seed, multiplayer = m.group(1), int(m.group(2)), m.group(3), True
        cm = re.search(rf'Player {re.escape(config.STEAM_ID)}, ([A-Z_]+)', players_str)
        character = cm.group(1) if cm else "Unknown"
        parser.set_player_prefix(f"Player {config.STEAM_ID}")
        save_reader.set_mode(True)
        _start_run(character, ascension, seed, multiplayer)
        return

    if _run is None:
        return

    # Track loss
    if "has lost to encounter" in raw:
        _result = False

    # Add events to CURRENT floor first, CombatReward belongs to the floor
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
            if _last_max_health is not None:
                _prev_floor_max_health = _last_max_health
            _merchant_snapshot = None

    # Run end — write JSON
    m = re.search(r'Saved run history: (\S+)\.run', raw)
    if m:
        run_id = m.group(1)
        _run["run_id"] = run_id
        result = save_reader.read_run_result(run_id)
        _run["result"] = result if result is not None else _result
        db.insert_run(_run)
        _run = None
        _result = True
