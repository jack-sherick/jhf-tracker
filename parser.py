import re
from logtypes import CardPlayed, PotionUsed, MonsterPlayed, Encounter, CombatReward, RarityStats, MerchantAction

# module state (I wish this was Haskell too)
_act = 0
_floor = 0
_turn = 0
_in_player_turn = False
_rarity_buf: list[tuple[float, float]] = []
_reward: dict | None = None
_current_room: str | None = None  # tracks room type between preload and MapVote
_player_prefix = "Player 1"  # player 1 for singleplayer / player {STEAM_ID} for multiplayer


def set_player_prefix(prefix: str):
    global _player_prefix
    _player_prefix = prefix


def _flush_reward() -> list:
    global _reward
    if _reward is None:
        return []
    r = CombatReward(
        gold=_reward.get("gold", 0),
        card=_reward.get("card"),
        potion=_reward.get("potion"),
        relic=_reward.get("relic"),
        floor=_floor,
    )
    _reward = None
    return [r]


def parse(log: str) -> list:
    global _act, _floor, _turn, _in_player_turn, _rarity_buf, _reward, _current_room

    log = log.strip()

    # Floor tracking: flush any pending reward before moving to next room
    if "->MapVote" in log:
        m = re.search(r'gen: (\d+) coord: \(\d+, (\d+)\)', log)
        if m:
            events = _flush_reward()
            _act = int(m.group(1))
            _floor = int(m.group(2))
            _turn = 0
            _in_player_turn = False
            _current_room = None
            return events
        return []

    # Non-combat room types — track current room for context
    for room_type in ("Event", "RestSite", "Merchant", "Treasure"):
        if f"[INFO] Preloading '{room_type} Room'" in log and "Complete" not in log:
            _current_room = room_type
            return [Encounter(room=room_type, mode=room_type, encounter=None, floor=_floor)]

    # Encounter start
    if "[INFO] Creating NCombatRoom" in log:
        m = re.search(r'mode=(\S+) encounter=(\S+?)\.?$', log)
        if m:
            _turn = 0
            _in_player_turn = False
            _current_room = "Combat"
            return [Encounter(room="Combat", mode=m.group(1), encounter=m.group(2), floor=_floor)]
        return []

    # Merchant: chose cards = card purchased (non-empty) or card cut (need save diff to distinguish)
    if f"[INFO] {_player_prefix} chose cards" in log and _current_room == "Merchant":
        m = re.search(r'chose cards \[([^\]]*)\]', log)
        if m:
            cards = [c.strip() for c in m.group(1).split(",") if c.strip()]
            if cards:
                return [MerchantAction(action="card_cuts_purchased", items=cards, floor=_floor)]
        return []

    # Card played
    if f"[INFO] {_player_prefix} playing card" in log:
        m = re.search(rf'\[INFO\] {re.escape(_player_prefix)} playing card (\S+) \((.+)\)', log)
        if m:
            if not _in_player_turn:
                _turn += 1
                _in_player_turn = True
            target = None if m.group(2) == "no target" else m.group(2)
            return [CardPlayed(player_id=_player_prefix, character="", card=m.group(1), target=target, turn=_turn, floor=_floor)]
        return []

    # Potion used
    if f"[INFO] {_player_prefix} using potion" in log:
        m = re.search(rf'\[INFO\] {re.escape(_player_prefix)} using potion (\S+) \((.+)\)', log)
        if m:
            if not _in_player_turn:
                _turn += 1
                _in_player_turn = True
            target = None if m.group(2) == "no target" else m.group(2)
            return [PotionUsed(player_id=_player_prefix, character="", potion=m.group(1), target=target, turn=_turn, floor=_floor)]
        return []

    # Monster move - ends the player's turn
    if "[INFO] Monster" in log and "performing move" in log:
        m = re.match(r'\[INFO\] Monster (\S+) performing move (\S+)', log)
        if m:
            _in_player_turn = False
            return [MonsterPlayed(monster=m.group(1), move=m.group(2), turn=_turn, floor=_floor)]
        return []

    # Combat rewards
    if "[INFO] Obtained" in log:
        m = re.search(r'Obtained (\d+) gold from reward', log)
        if m:
            if _reward is None:
                _reward = {}
            _reward["gold"] = _reward.get("gold", 0) + int(m.group(1))
            return []

        m = re.search(r'Obtained CARD\.(\S+) from card reward', log)
        if m:
            if _reward is None:
                _reward = {}
            _reward.setdefault("card", []).append(m.group(1))
            return []

        m = re.search(r'Obtained POTION\.(\S+) from potion reward', log)
        if m:
            if _reward is None:
                _reward = {}
            _reward["potion"] = m.group(1)
            return []

        m = re.search(r'Obtained RELIC\.(\S+) from relic reward', log)
        if m:
            if _reward is None:
                _reward = {}
            _reward["relic"] = m.group(1)
            return []

        return []

    # Rarity stats
    if "[INFO] Card rarity:" in log:
        m = re.search(r'Rolled ([^\s,]+), need < [^\s]+ for rare \(offset = ([^\s)]+)\)', log)
        if m:
            _rarity_buf.append((float(m.group(1)), float(m.group(2))))
            if len(_rarity_buf) == 3:
                a, b, c = _rarity_buf
                _rarity_buf = []
                return [RarityStats(
                    a_rarity=a[0], a_offset=a[1],
                    b_rarity=b[0], b_offset=b[1],
                    c_rarity=c[0], c_offset=c[1],
                    floor=_floor,
                )]
        return []

    return []
