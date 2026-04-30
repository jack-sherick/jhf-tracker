import json
import psycopg2

import config


def _connect():
    return psycopg2.connect(config.DB_URL)


def insert_run(run: dict):
    floors = run.get("floors", {})
    floor_reached = run.get("floor_reached", 0)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (run_id, player_id, character, ascension, seed, result,
                                  floor_reached, gold, health, max_health, deck)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                ),
            )

            for floor in floors.values():
                reward = floor.get("reward") or {}
                cur.execute(
                    """
                    INSERT INTO floors (run_id, act, floor, encounter, mode,
                                       cards_played, potions_used, monster_moves, rarity_stats,
                                       reward_gold, reward_card, reward_potion, reward_relic,
                                       health, max_health, health_lost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        reward.get("card"),
                        reward.get("potion"),
                        reward.get("relic"),
                        floor.get("health"),
                        floor.get("max_health"),
                        floor.get("health_lost"),
                    ),
                )

    print(f"[db] Inserted run {run['run_id']} with {len(floors)} floors")
