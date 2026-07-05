import time

from core.database import get_connection


def update_wallet_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            wallet_address,
            COUNT(*) AS resolved_buy_trades,
            SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN won = 0 THEN 1 ELSE 0 END) AS losses,
            SUM(
                CASE
                    WHEN won = 1 THEN (1 - price) * size
                    ELSE -price * size
                END
            ) AS pnl,
            SUM(price * size) AS cost_basis
        FROM trades
        WHERE resolved = 1
          AND side = 'BUY'
        GROUP BY wallet_address
        """
    )

    rows = cur.fetchall()
    updated = 0

    for row in rows:
        wallet_address = row["wallet_address"]
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        resolved_buy_trades = row["resolved_buy_trades"] or 0
        pnl = row["pnl"] or 0
        cost_basis = row["cost_basis"] or 0

        if resolved_buy_trades > 0:
            win_rate = (wins / resolved_buy_trades) * 100
        else:
            win_rate = 0

        if cost_basis > 0:
            roi = (pnl / cost_basis) * 100
        else:
            roi = 0

        cur.execute(
            """
            UPDATE wallets
            SET
                wins = ?,
                losses = ?,
                win_rate = ?,
                roi = ?
            WHERE wallet_address = ?
            """,
            (
                wins,
                losses,
                round(win_rate, 2),
                round(roi, 2),
                wallet_address,
            ),
        )

        updated += 1

    conn.commit()
    conn.close()

    return {
        "updated_wallets": updated,
        "timestamp": int(time.time()),
    }


def wallet_stats_preview(limit: int = 25):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            wallet_address,
            total_trades,
            wins,
            losses,
            win_rate,
            roi,
            score,
            last_seen
        FROM wallets
        WHERE wins > 0 OR losses > 0
        ORDER BY win_rate DESC, roi DESC, total_trades DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows