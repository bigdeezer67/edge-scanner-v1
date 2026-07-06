import time

from core.database import get_connection


def get_market_timeline(condition_id: str, limit: int = 100):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            t.trade_id,
            t.wallet_address,
            t.condition_id,
            t.market_slug,
            t.side,
            t.outcome,
            t.price,
            t.size,
            t.timestamp,
            t.resolved,
            t.won,
            w.score AS wallet_score,
            w.win_rate,
            w.roi,
            w.total_trades
        FROM trades t
        LEFT JOIN wallets w
            ON t.wallet_address = w.wallet_address
        WHERE t.condition_id = ?
        ORDER BY t.timestamp ASC
        LIMIT ?
        """,
        (condition_id, limit),
    )

    trades = [dict(row) for row in cur.fetchall()]
    conn.close()

    timeline = []

    for index, trade in enumerate(trades):
        timeline.append(
            {
                "sequence": index + 1,
                "event_type": "TRADE",
                "timestamp": trade["timestamp"],
                "wallet_address": trade["wallet_address"],
                "side": trade["side"],
                "outcome": trade["outcome"],
                "price": trade["price"],
                "size": trade["size"],
                "wallet_score": trade["wallet_score"],
                "wallet_win_rate": trade["win_rate"],
                "wallet_roi": trade["roi"],
                "wallet_total_trades": trade["total_trades"],
                "resolved": trade["resolved"],
                "won": trade["won"],
                "description": _build_description(trade),
            }
        )

    return {
        "status": "ok",
        "condition_id": condition_id,
        "events_found": len(timeline),
        "timeline": timeline,
        "timestamp": int(time.time()),
    }


def _build_description(trade):
    wallet = trade["wallet_address"]

    if wallet:
        short_wallet = f"{wallet[:6]}...{wallet[-4:]}"
    else:
        short_wallet = "Unknown wallet"

    return (
        f"{short_wallet} {trade['side']} {trade['outcome']} "
        f"at {trade['price']} for size {trade['size']}."
    )