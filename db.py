import json
import psycopg2

import config


def _connect():
    return psycopg2.connect(config.DB_URL)


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def insert_run(run: dict):
    floors = run.get("floors", {})
    floor_reached = run.get("floor_reached", 0)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (run_id, player_id, character, ascension, seed, result,
                                  floor_reached, gold, health, max_health, deck, relics, multiplayer, patch)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                (
                    run["run_id"],
                    run.get("player_id", config.PLAYER_ID),
                    run["character"],
                    run["ascension"],
                    run["seed"],
                    run["result"],
                    floor_reached,
                    run.get("gold", 0),
                    run.get("health"),
                    run.get("max_health"),
                    json.dumps(run.get("deck", [])),
                    json.dumps(run.get("relics", [])),
                    run.get("multiplayer", False),
                    run.get("patch"),
                ),
            )

            for floor in floors.values():
                reward = floor.get("reward") or {}
                cur.execute(
                    """
                    INSERT INTO floors (run_id, act, floor, encounter, mode,
                                       cards_played, potions_used, monster_moves, rarity_stats,
                                       reward_gold, reward_card, reward_potion, reward_relic,
                                       health, max_health, health_lost, max_health_lost,
                                       character, relics, floor_gold,
                                       cards_purchased, relics_purchased, potions_purchased, card_cuts_purchased,
                                       multiplayer, patch, deck_snapshot)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run["run_id"],
                        floor["act"],
                        floor["floor"],
                        floor.get("encounter"),
                        floor.get("mode"),
                        json.dumps(floor.get("cards_played", [])),
                        json.dumps(floor.get("potions_used", [])),
                        json.dumps(floor.get("monster_moves", [])),
                        json.dumps(floor.get("rarity_stats")),
                        reward.get("gold"),
                        json.dumps(_as_list(reward.get("card"))),
                        reward.get("potion"),
                        reward.get("relic"),
                        floor.get("health"),
                        floor.get("max_health"),
                        floor.get("health_lost"),
                        floor.get("max_health_lost"),
                        floor.get("character"),
                        json.dumps(floor.get("relics", [])),
                        floor.get("floor_gold"),
                        json.dumps(floor.get("cards_purchased", [])),
                        json.dumps(floor.get("relics_purchased", [])),
                        json.dumps(floor.get("potions_purchased", [])),
                        json.dumps(floor.get("card_cuts_purchased", [])),
                        run.get("multiplayer", False),
                        run.get("patch"),
                        json.dumps(floor.get("deck_snapshot", [])),
                    ),
                )

    print(f"[db] Inserted run {run['run_id']} with {len(floors)} floors")

    conn = _connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        for view in ("cards", "encounters", "events", "relics"):
            try:
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
            except Exception as e:
                print(f"[db] Failed to refresh {view}: {e}")
    conn.close()
