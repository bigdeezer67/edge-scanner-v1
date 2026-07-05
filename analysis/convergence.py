import time

from core.database import get_connection


def detect_convergence(
    window_seconds: int = 300,
    min_wallets: int = 3,
    min_avg_score: float = 20,
    limit: int = 25,
):
    now = int(time.time())
    since = now - window_seconds

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            t.condition_id,
            t.market_slug,
            t.outcome,
            t.side,
            COUNT(DISTINCT t.wallet_address) AS wallet_count,
            AVG(t.price) AS avg_entry,
            SUM(t.size) AS total_size,
            AVG(w.score) AS avg_wallet_score,
            SUM(w.score) AS combined_score,
            MIN(t.timestamp) AS first_seen,
            MAX(t.timestamp) AS last_seen
        FROM trades t
        JOIN wallets w
            ON t.wallet_address = w.wallet_address
        WHERE t.timestamp >= ?
          AND t.side = 'BUY'
        GROUP BY
            t.condition_id,
            t.market_slug,
            t.outcome,
            t.side
        HAVING wallet_count >= ?
           AND avg_wallet_score >= ?
        ORDER BY combined_score DESC, wallet_count DESC, total_size DESC
        LIMIT ?
        """,
        (since, min_wallets, min_avg_score, limit),
    )

    rows = [dict(row) for row in cur.fetchall()]

    signals = []

    for row in rows:
        condition_id = row["condition_id"]
        outcome = row["outcome"]

        cur.execute(
            """
            SELECT
                t.wallet_address,
                t.price,
                t.size,
                t.timestamp,
                w.score,
                w.total_trades,
                w.win_rate,
                w.roi
            FROM trades t
            JOIN wallets w
                ON t.wallet_address = w.wallet_address
            WHERE t.timestamp >= ?
              AND t.condition_id = ?
              AND t.outcome = ?
              AND t.side = 'BUY'
            ORDER BY w.score DESC, t.size DESC
            LIMIT 10
            """,
            (since, condition_id, outcome),
        )

        wallets = [dict(wallet) for wallet in cur.fetchall()]

        signal_strength = calculate_signal_strength(
            wallet_count=row["wallet_count"],
            avg_wallet_score=row["avg_wallet_score"],
            total_size=row["total_size"],
            window_seconds=window_seconds,
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )

        signals.append(
            {
                "condition_id": condition_id,
                "market_slug": row["market_slug"],
                "outcome": outcome,
                "side": row["side"],
                "wallet_count": row["wallet_count"],
                "avg_entry": round(row["avg_entry"] or 0, 4),
                "total_size": round(row["total_size"] or 0, 2),
                "avg_wallet_score": round(row["avg_wallet_score"] or 0, 2),
                "combined_score": round(row["combined_score"] or 0, 2),
                "signal_strength": signal_strength,
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
                "wallets": wallets,
            }
        )

    conn.close()

    return {
        "window_seconds": window_seconds,
        "min_wallets": min_wallets,
        "min_avg_score": min_avg_score,
        "signals_found": len(signals),
        "signals": signals,
        "timestamp": now,
    }


def calculate_signal_strength(
    wallet_count,
    avg_wallet_score,
    total_size,
    window_seconds,
    first_seen,
    last_seen,
):
    wallet_component = min(wallet_count / 5, 1) * 35
    score_component = min((avg_wallet_score or 0) / 100, 1) * 35
    size_component = min((total_size or 0) / 5000, 1) * 20

    spread_seconds = max((last_seen or 0) - (first_seen or 0), 1)
    timing_component = max(0, 1 - (spread_seconds / window_seconds)) * 10

    strength = (
        wallet_component
        + score_component
        + size_component
        + timing_component
    )

    return round(strength, 2)