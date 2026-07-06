import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "edge.db"

DATA_DIR.mkdir(exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(cur, table_name, column_name, column_definition):
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in cur.fetchall()]

    if column_name not in columns:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS markets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition_id TEXT UNIQUE,
        question TEXT,
        slug TEXT,
        active INTEGER,
        closed INTEGER,
        volume REAL,
        liquidity REAL,
        raw_json TEXT,
        created_at INTEGER,
        updated_at INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition_id TEXT,
        volume REAL,
        liquidity REAL,
        timestamp INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address TEXT UNIQUE,
        total_trades INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        roi REAL DEFAULT 0,
        score REAL DEFAULT 0,
        first_seen INTEGER,
        last_seen INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id TEXT UNIQUE,
        wallet_address TEXT,
        condition_id TEXT,
        market_slug TEXT,
        side TEXT,
        outcome TEXT,
        price REAL,
        size REAL,
        timestamp INTEGER,
        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_uuid TEXT UNIQUE,
        condition_id TEXT,
        market_slug TEXT,
        outcome TEXT,
        side TEXT,
        status TEXT DEFAULT 'NEW',
        confidence REAL DEFAULT 0,
        conviction_score REAL DEFAULT 0,
        pressure_score REAL DEFAULT 0,
        convergence_score REAL DEFAULT 0,
        opposition_penalty REAL DEFAULT 0,
        wallet_count INTEGER DEFAULT 0,
        avg_wallet_score REAL DEFAULT 0,
        total_size REAL DEFAULT 0,
        avg_entry REAL DEFAULT 0,
        created_at INTEGER,
        updated_at INTEGER,
        resolved_at INTEGER,
        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signal_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_uuid TEXT,
        event_type TEXT,
        old_status TEXT,
        new_status TEXT,
        old_confidence REAL,
        new_confidence REAL,
        details_json TEXT,
        created_at INTEGER
    )
    """)

    add_column_if_missing(cur, "markets", "resolved", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "markets", "winning_outcome", "TEXT")
    add_column_if_missing(cur, "markets", "resolved_at", "INTEGER")

    add_column_if_missing(cur, "trades", "resolved", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "trades", "won", "INTEGER")
    add_column_if_missing(cur, "trades", "resolved_at", "INTEGER")
    add_column_if_missing(cur, "signals", "signal_uuid", "TEXT")
    add_column_if_missing(cur, "signals", "outcome", "TEXT")
    add_column_if_missing(cur, "signals", "confidence", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "conviction_score", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "pressure_score", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "convergence_score", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "opposition_penalty", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "avg_wallet_score", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "total_size", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "resolved_at", "INTEGER")
    add_column_if_missing(cur, "signals", "resolved_at", "INTEGER")
    add_column_if_missing(cur, "signals", "side", "TEXT")
    add_column_if_missing(cur, "signals", "status", "TEXT DEFAULT 'NEW'")
    add_column_if_missing(cur, "signals", "wallet_count", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "signals", "avg_entry", "REAL DEFAULT 0")
    add_column_if_missing(cur, "signals", "created_at", "INTEGER")
    add_column_if_missing(cur, "signals", "updated_at", "INTEGER")
    add_column_if_missing(cur, "signals", "raw_json", "TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_condition ON trades(condition_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet_address)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_uuid ON signals(signal_uuid)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_condition ON signals(condition_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signal_events_uuid ON signal_events(signal_uuid)")

    conn.commit()
    conn.close()


def db_stats():
    conn = get_connection()
    cur = conn.cursor()

    tables = [
        "markets",
        "market_snapshots",
        "wallets",
        "trades",
        "signals",
        "signal_events",
    ]

    stats = {}

    for table in tables:
        cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
        stats[table] = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM markets WHERE resolved = 1")
    stats["resolved_markets"] = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM trades WHERE resolved = 1")
    stats["resolved_trades"] = cur.fetchone()["count"]

    conn.close()
    return stats