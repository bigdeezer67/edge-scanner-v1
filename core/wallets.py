from core.database import get_connection


def get_top_wallets(limit: int = 25):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            wallet_address,
            total_trades,
            first_seen,
            last_seen,
            win_rate,
            roi,
            score
        FROM wallets
        ORDER BY total_trades DESC
        LIMIT ?
        """,
        (limit,),
    )

    wallets = [dict(row) for row in cur.fetchall()]

    conn.close()
    return wallets