from dataclasses import dataclass

@dataclass
# RUN INFORMATION - comes from save file (change occurs on save write action)
class RunInfo:
    player_id: str
    character: str
    deck: list
    gold: int
    health: int
    max_health: int
    potions: list[str] | None

    floor: int

# LOG TYPES - comes from listening to godot.log (change occurs on game state change)
@dataclass
class CardPlayed:
    player_id: str
    character: str
    card: str
    target: str | None

    turn: int
    floor: int

@dataclass
class PotionUsed:
    player_id: str
    character: str
    potion: str
    target: str | None

    turn: int
    floor: int

@dataclass
class MonsterPlayed:
    monster: str
    move: str

    turn: int
    floor: int

@dataclass
class Encounter:
    room: str
    mode: str
    encounter: str

    floor: int

@dataclass
class CombatReward:
    gold: int
    card: str | None
    potion: str | None
    relic: str | None

    floor: int

@dataclass
class RarityStats:
    a_rarity: float
    a_offset: float

    b_rarity: float
    b_offset: float

    c_rarity: float
    c_offset: float

    floor: int

@dataclass
class RestSite:
    rest: str | None
    smith: str | None
    event: list[str] | None

    floor: int

@dataclass
class Event:
    event: str

    floor: int

LogEvent = CardPlayed | PotionUsed | MonsterPlayed | Encounter | CombatReward | RarityStats | RestSite