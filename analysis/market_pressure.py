import time

from core.database import get_connection


def calculate_market_pressure(
    window_seconds: int = 900,
    min_total_size: float = 0,
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
            COUNT(*) AS trade_count,
            COUNT(DISTINCT t.wallet_address) AS wallet_count,
            SUM(t.size) AS total_size,
            AVG(t.price) AS avg_price,
            AVG(w.score) AS avg_wallet_score,
            SUM(w.score * t.size) AS weighted_pressure,
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
        HAVING total_size >= ?
        ORDER BY weighted_pressure DESC
        LIMIT ?
        """,
        (since, min_total_size, limit),
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    results = []

    for row in rows:
        pressure_score = _pressure_score(
            wallet_count=row["wallet_count"],
            total_size=row["total_size"],
            avg_wallet_score=row["avg_wallet_score"],
            window_seconds=window_seconds,
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )

        results.append(
            {
                "condition_id": row["condition_id"],
                "market_slug": row["market_slug"],
                "outcome": row["outcome"],
                "side": row["side"],
                "trade_count": row["trade_count"],
                "wallet_count": row["wallet_count"],
                "total_size": round(row["total_size"] or 0, 2),
                "avg_price": round(row["avg_price"] or 0, 4),
                "avg_wallet_score": round(row["avg_wallet_score"] or 0, 2),
                "weighted_pressure": round(row["weighted_pressure"] or 0, 2),
                "pressure_score": pressure_score,
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
            }
        )

    return {
        "window_seconds": window_seconds,
        "markets_found": len(results),
        "markets": results,
        "timestamp": now,
    }


def _pressure_score(
    wallet_count,
    total_size,
    avg_wallet_score,
    window_seconds,
    first_seen,
    last_seen,
):
    wallet_component = min((wallet_count or 0) / 5, 1) * 30
    size_component = min((total_size or 0) / 5000, 1) * 25
    quality_component = min((avg_wallet_score or 0) / 100, 1) * 35

    spread_seconds = max((last_seen or 0) - (first_seen or 0), 1)
    speed_component = max(0, 1 - (spread_seconds / window_seconds)) * 10

    return round(
        wallet_component
        + size_component
        + quality_component
        + speed_component,
        2,
    )