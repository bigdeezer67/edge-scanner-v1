import time

from core.database import get_connection


def detect_opposition(
    window_seconds: int = 900,
    min_wallet_score: float = 10,
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
            COUNT(DISTINCT t.wallet_address) AS wallet_count,
            SUM(t.size) AS total_size,
            AVG(w.score) AS avg_wallet_score,
            SUM(w.score * t.size) AS weighted_size
        FROM trades t
        JOIN wallets w
            ON t.wallet_address = w.wallet_address
        WHERE t.timestamp >= ?
          AND t.side = 'BUY'
          AND w.score >= ?
        GROUP BY
            t.condition_id,
            t.market_slug,
            t.outcome
        ORDER BY t.condition_id, weighted_size DESC
        """,
        (since, min_wallet_score),
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    by_market = {}

    for row in rows:
        condition_id = row["condition_id"]
        by_market.setdefault(condition_id, []).append(row)

    conflicts = []

    for condition_id, outcomes in by_market.items():
        if len(outcomes) < 2:
            continue

        sorted_outcomes = sorted(
            outcomes,
            key=lambda x: x["weighted_size"] or 0,
            reverse=True,
        )

        leader = sorted_outcomes[0]
        challenger = sorted_outcomes[1]

        leader_weight = leader["weighted_size"] or 0
        challenger_weight = challenger["weighted_size"] or 0

        if leader_weight <= 0:
            continue

        opposition_ratio = challenger_weight / leader_weight

        conflicts.append(
            {
                "condition_id": condition_id,
                "market_slug": leader["market_slug"],
                "leading_outcome": leader["outcome"],
                "opposing_outcome": challenger["outcome"],
                "leader_weighted_size": round(leader_weight, 2),
                "opposer_weighted_size": round(challenger_weight, 2),
                "opposition_ratio": round(opposition_ratio, 4),
                "opposition_level": _opposition_level(opposition_ratio),
            }
        )

    conflicts = sorted(
        conflicts,
        key=lambda x: x["opposition_ratio"],
        reverse=True,
    )[:limit]

    return {
        "window_seconds": window_seconds,
        "conflicts_found": len(conflicts),
        "conflicts": conflicts,
        "timestamp": now,
    }


def _opposition_level(ratio: float):
    if ratio >= 0.75:
        return "HIGH"
    if ratio >= 0.4:
        return "MEDIUM"
    if ratio >= 0.2:
        return "LOW"
    return "NONE"