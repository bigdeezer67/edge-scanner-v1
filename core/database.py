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
        condition_id TEXT,
        market_slug TEXT,
        side TEXT,
        wallet_count INTEGER,
        combined_score REAL,
        avg_entry REAL,
        signal_strength REAL,
        status TEXT DEFAULT 'PAPER',
        created_at INTEGER,
        raw_json TEXT
    )
    """)

    conn.commit()
    conn.close()


def db_stats():
    conn = get_connection()
    cur = conn.cursor()

    tables = ["markets", "market_snapshots", "wallets", "trades", "signals"]
    stats = {}

    for table in tables:
        cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
        stats[table] = cur.fetchone()["count"]

    conn.close()
    return stats