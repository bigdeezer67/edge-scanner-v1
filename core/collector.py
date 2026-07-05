import json
import time

from core.database import get_connection
from core.gamma import get_active_markets


def save_markets(limit: int = 50):
    markets = get_active_markets(limit=limit)
    now = int(time.time())

    conn = get_connection()
    cur = conn.cursor()

    saved = 0

    for market in markets:
        condition_id = market.get("conditionId") or market.get("condition_id")
        question = market.get("question")
        slug = market.get("slug")
        active = 1 if market.get("active") else 0
        closed = 1 if market.get("closed") else 0
        volume = float(market.get("volume") or 0)
        liquidity = float(market.get("liquidity") or 0)

        if not condition_id:
            continue

        cur.execute(
            """
            INSERT INTO markets (
                condition_id,
                question,
                slug,
                active,
                closed,
                volume,
                liquidity,
                raw_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(condition_id) DO UPDATE SET
                question=excluded.question,
                slug=excluded.slug,
                active=excluded.active,
                closed=excluded.closed,
                volume=excluded.volume,
                liquidity=excluded.liquidity,
                raw_json=excluded.raw_json,
                updated_at=excluded.updated_at
            """,
            (
                condition_id,
                question,
                slug,
                active,
                closed,
                volume,
                liquidity,
                json.dumps(market),
                now,
                now,
            ),
        )

        cur.execute(
            """
            INSERT INTO market_snapshots (
                condition_id,
                volume,
                liquidity,
                timestamp
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                condition_id,
                volume,
                liquidity,
                now,
            ),
        )

        saved += 1

    conn.commit()
    conn.close()

    return {
        "saved": saved,
        "timestamp": now,
    }