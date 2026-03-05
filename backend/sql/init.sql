-- ============================================================
--  SENTINEL — TimescaleDB Schema
--  Run automatically by Docker on first container start
-- ============================================================

-- ── Aircraft positions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS aircraft_positions (
    time         TIMESTAMPTZ       NOT NULL,
    icao24       TEXT              NOT NULL,
    callsign     TEXT,
    lat          DOUBLE PRECISION,
    lon          DOUBLE PRECISION,
    altitude_m   DOUBLE PRECISION,
    speed_kts    DOUBLE PRECISION,
    heading      SMALLINT,
    vert_rate    REAL,
    squawk       TEXT,
    country      TEXT,
    military     BOOLEAN           DEFAULT FALSE,
    on_ground    BOOLEAN           DEFAULT FALSE
);

SELECT create_hypertable(
    'aircraft_positions', 'time',
    if_not_exists => TRUE
);

-- Fast per-aircraft history queries
CREATE INDEX IF NOT EXISTS idx_ac_icao_time
    ON aircraft_positions (icao24, time DESC);

-- TimescaleDB columnar compression (dramatically reduces disk)
ALTER TABLE aircraft_positions SET (
    timescaledb.compress,
    timescaledb.compress_orderby    = 'time DESC',
    timescaledb.compress_segmentby  = 'icao24'
);

-- Compress chunks older than 1 hour
SELECT add_compression_policy(
    'aircraft_positions',
    INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Auto-drop data older than 7 days
SELECT add_retention_policy(
    'aircraft_positions',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ── Ship positions ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ship_positions (
    time         TIMESTAMPTZ       NOT NULL,
    mmsi         TEXT              NOT NULL,
    name         TEXT,
    lat          DOUBLE PRECISION,
    lon          DOUBLE PRECISION,
    speed        REAL,
    heading      SMALLINT,
    course       SMALLINT,
    ship_type    SMALLINT,
    status       TEXT,
    destination  TEXT
);

SELECT create_hypertable(
    'ship_positions', 'time',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_ship_mmsi_time
    ON ship_positions (mmsi, time DESC);

ALTER TABLE ship_positions SET (
    timescaledb.compress,
    timescaledb.compress_orderby    = 'time DESC',
    timescaledb.compress_segmentby  = 'mmsi'
);

SELECT add_compression_policy(
    'ship_positions',
    INTERVAL '2 hours',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'ship_positions',
    INTERVAL '3 days',
    if_not_exists => TRUE
);
