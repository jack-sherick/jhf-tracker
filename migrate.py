import psycopg2
import config

MIGRATION = """
ALTER TABLE runs ADD COLUMN IF NOT EXISTS relics JSONB DEFAULT '[]';

CREATE MATERIALIZED VIEW IF NOT EXISTS encounters AS
SELECT
    f.encounter,
    f.mode,
    COALESCE(f.character, r.character) AS character,
    r.ascension,
    r.multiplayer,
    COUNT(*) AS appearances,
    COUNT(DISTINCT f.run_id) AS run_appearances,
    ROUND(AVG(COALESCE(f.health_lost, 0))::numeric, 2) AS avg_health_lost,
    ROUND(AVG(COALESCE(f.max_health_lost, 0))::numeric, 2) AS avg_max_health_lost,
    ROUND(
        COUNT(DISTINCT CASE WHEN r.result = true THEN f.run_id END)::numeric /
        NULLIF(COUNT(DISTINCT f.run_id)::numeric, 0),
        4
    ) AS win_rate
FROM floors f
JOIN runs r USING (run_id)
WHERE f.mode IN ('ActiveCombat', 'VisualOnly')
  AND f.encounter IS NOT NULL
GROUP BY f.encounter, f.mode, COALESCE(f.character, r.character), r.ascension, r.multiplayer;

CREATE UNIQUE INDEX IF NOT EXISTS encounters_idx
ON encounters (encounter, mode, character, ascension, multiplayer);

CREATE MATERIALIZED VIEW IF NOT EXISTS events AS
SELECT
    f.encounter AS event_name,
    COALESCE(f.character, r.character) AS character,
    r.ascension,
    r.multiplayer,
    COUNT(*) AS appearances,
    COUNT(DISTINCT f.run_id) AS run_appearances,
    ROUND(
        COUNT(DISTINCT CASE WHEN r.result = true THEN f.run_id END)::numeric /
        NULLIF(COUNT(DISTINCT f.run_id)::numeric, 0),
        4
    ) AS win_rate
FROM floors f
JOIN runs r USING (run_id)
WHERE f.mode = 'Event'
  AND f.encounter IS NOT NULL
GROUP BY f.encounter, COALESCE(f.character, r.character), r.ascension, r.multiplayer;

CREATE UNIQUE INDEX IF NOT EXISTS events_idx
ON events (event_name, character, ascension, multiplayer);

CREATE MATERIALIZED VIEW IF NOT EXISTS relics AS
WITH relic_appearances AS (
    SELECT
        r.run_id,
        r.result,
        r.character,
        r.ascension,
        r.multiplayer,
        replace(relic.value->>'id', 'RELIC.', '') AS relic_id
    FROM runs r
    CROSS JOIN LATERAL jsonb_array_elements(r.relics) relic(value)
    WHERE r.relics IS NOT NULL AND jsonb_array_length(r.relics) > 0
)
SELECT
    relic_id,
    character,
    ascension,
    multiplayer,
    COUNT(DISTINCT run_id) AS appearances,
    ROUND(
        COUNT(DISTINCT CASE WHEN result = true THEN run_id END)::numeric /
        NULLIF(COUNT(DISTINCT run_id)::numeric, 0),
        4
    ) AS win_rate
FROM relic_appearances
GROUP BY relic_id, character, ascension, multiplayer;

CREATE UNIQUE INDEX IF NOT EXISTS relics_idx
ON relics (relic_id, character, ascension, multiplayer);
"""

if __name__ == "__main__":
    with psycopg2.connect(config.DB_URL) as conn:
        with conn.cursor() as cur:
            for statement in MIGRATION.strip().split(";"):
                statement = statement.strip()
                if statement:
                    print(f"Running: {statement[:60]}...")
                    cur.execute(statement)
    print("Migration complete.")
