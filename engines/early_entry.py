import time

from core.database import get_connection


def calculate_early_entry_scores(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            t.wallet_address,
            t.condition_id,
            t.market_slug,
            MIN(t.timestamp) AS first_entry,
            SUM(t.size) AS total_size,
            AVG(t.price) AS avg_entry,
            MAX(t.won) AS won,
            w.score AS wallet_score,
            w.win_rate,
            w.roi,
            w.total_trades
        FROM trades t
        JOIN wallets w
            ON t.wallet_address = w.wallet_address
        WHERE t.resolved = 1
          AND t.side = 'BUY'
        GROUP BY
            t.wallet_address,
            t.condition_id,
            t.market_slug
        """
    )

    entries = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        SELECT
            condition_id,
            MIN(timestamp) AS market_first_trade,
            MAX(timestamp) AS market_last_trade
        FROM trades
        WHERE side = 'BUY'
        GROUP BY condition_id
        """
    )

    market_windows = {
        row["condition_id"]: dict(row)
        for row in cur.fetchall()
    }

    conn.close()

    scored_entries = []

    for entry in entries:
        window = market_windows.get(entry["condition_id"])
        if not window:
            continue

        market_first = window["market_first_trade"]
        market_last = window["market_last_trade"]

        if not market_first or not market_last or market_last <= market_first:
            timing_score = 50
        else:
            position = (entry["first_entry"] - market_first) / (market_last - market_first)
            timing_score = max(0, min(100, 100 - (position * 100)))

        accuracy_score = 100 if entry["won"] == 1 else 0
        wallet_quality = entry["wallet_score"] or 0

        early_alpha_score = (
            timing_score * 0.45
            + accuracy_score * 0.35
            + wallet_quality * 0.20
        )

        scored_entries.append(
            {
                "wallet_address": entry["wallet_address"],
                "condition_id": entry["condition_id"],
                "market_slug": entry["market_slug"],
                "first_entry": entry["first_entry"],
                "total_size": round(entry["total_size"] or 0, 2),
                "avg_entry": round(entry["avg_entry"] or 0, 4),
                "won": entry["won"],
                "wallet_score": round(wallet_quality, 2),
                "timing_score": round(timing_score, 2),
                "accuracy_score": accuracy_score,
                "early_alpha_score": round(early_alpha_score, 2),
            }
        )

    scored_entries = sorted(
        scored_entries,
        key=lambda x: x["early_alpha_score"],
        reverse=True,
    )[:limit]

    return {
        "status": "ok",
        "entries_found": len(scored_entries),
        "entries": scored_entries,
        "timestamp": int(time.time()),
    }