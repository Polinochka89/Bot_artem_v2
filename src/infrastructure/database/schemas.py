from __future__ import annotations

PRAGMA_STATEMENTS: tuple[str, ...] = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
)

CREATE_COLLECTION_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS collection_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at     TEXT    NOT NULL,
    finished_at    TEXT,
    prices_count   INTEGER DEFAULT 0,
    has_errors     INTEGER DEFAULT 0
);
"""

CREATE_PRICES_TABLE = """
CREATE TABLE IF NOT EXISTS prices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER REFERENCES collection_runs(id),
    symbol       TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    value        TEXT    NOT NULL,
    buy          TEXT,
    sell         TEXT,
    source       TEXT    NOT NULL,
    display_name TEXT    NOT NULL,
    emoji        TEXT    NOT NULL DEFAULT '',
    collected_at TEXT    NOT NULL,
    date         TEXT    NOT NULL,
    UNIQUE (symbol, category, date, source)
);
"""

CREATE_PRICES_LOOKUP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_prices_lookup
    ON prices (symbol, category, date);
"""
