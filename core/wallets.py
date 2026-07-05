from core.database import get_connection


def get_top_wallets(limit: int = 25):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            w.wallet_address,
            w.total_trades,
            w.first_seen,
            w.last_seen,
            w.win_rate,
            w.roi,
            w.score,
            COALESCE(AVG(t.price), 0) AS avg_price,
            COALESCE(AVG(t.size), 0) AS avg_size,
            COALESCE(SUM(t.size), 0) AS total_size,
            COUNT(DISTINCT t.condition_id) AS unique_markets
        FROM wallets w
        LEFT JOIN trades t
            ON w.wallet_address = t.wallet_address
        GROUP BY w.wallet_address
        ORDER BY w.total_trades DESC
        LIMIT ?
        """,
        (limit,),
    )

    wallets = [dict(row) for row in cur.fetchall()]
    conn.close()
    return wallets


def get_wallet_profile(wallet_address: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            w.wallet_address,
            w.total_trades,
            w.first_seen,
            w.last_seen,
            w.win_rate,
            w.roi,
            w.score,
            COALESCE(AVG(t.price), 0) AS avg_price,
            COALESCE(AVG(t.size), 0) AS avg_size,
            COALESCE(SUM(t.size), 0) AS total_size,
            COUNT(DISTINCT t.condition_id) AS unique_markets
        FROM wallets w
        LEFT JOIN trades t
            ON w.wallet_address = t.wallet_address
        WHERE w.wallet_address = ?
        GROUP BY w.wallet_address
        """,
        (wallet_address,),
    )

    wallet = cur.fetchone()

    if not wallet:
        conn.close()
        return None

    cur.execute(
        """
        SELECT
            trade_id,
            condition_id,
            market_slug,
            side,
            outcome,
            price,
            size,
            timestamp
        FROM trades
        WHERE wallet_address = ?
        ORDER BY timestamp DESC
        LIMIT 25
        """,
        (wallet_address,),
    )

    recent_trades = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        SELECT
            market_slug,
            COUNT(*) AS trade_count,
            SUM(size) AS total_size
        FROM trades
        WHERE wallet_address = ?
        GROUP BY market_slug
        ORDER BY trade_count DESC
        LIMIT 10
        """,
        (wallet_address,),
    )

    favorite_markets = [dict(row) for row in cur.fetchall()]

    conn.close()

    return {
        "wallet": dict(wallet),
        "recent_trades": recent_trades,
        "favorite_markets": favorite_markets,
    }