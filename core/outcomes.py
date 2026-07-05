import json
import time

from core.database import get_connection
from core.gamma import get_closed_markets


def parse_json_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []

    return []


def infer_winning_outcome(market):
    direct_fields = [
        "winningOutcome",
        "winning_outcome",
        "winner",
        "resolvedOutcome",
        "resolved_outcome",
    ]

    for field in direct_fields:
        value = market.get(field)
        if value:
            return str(value)

    outcomes = parse_json_list(market.get("outcomes"))
    prices = parse_json_list(market.get("outcomePrices"))

    if not outcomes or not prices or len(outcomes) != len(prices):
        return None

    numeric_prices = []

    for price in prices:
        try:
            numeric_prices.append(float(price))
        except Exception:
            numeric_prices.append(0)

    max_price = max(numeric_prices)

    if max_price < 0.98:
        return None

    winner_index = numeric_prices.index(max_price)
    return str(outcomes[winner_index])


def save_resolved_markets(limit: int = 100):
    closed_markets = get_closed_markets(limit=limit)
    now = int(time.time())

    conn = get_connection()
    cur = conn.cursor()

    saved_markets = 0
    resolved_trades = 0
    skipped = 0

    for market in closed_markets:
        condition_id = market.get("conditionId") or market.get("condition_id")
        question = market.get("question")
        slug = market.get("slug")
        volume = float(market.get("volume") or 0)
        liquidity = float(market.get("liquidity") or 0)
        winning_outcome = infer_winning_outcome(market)

        if not condition_id:
            skipped += 1
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
                updated_at,
                resolved,
                winning_outcome,
                resolved_at
            )
            VALUES (?, ?, ?, 0, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(condition_id) DO UPDATE SET
                question=excluded.question,
                slug=excluded.slug,
                active=0,
                closed=1,
                volume=excluded.volume,
                liquidity=excluded.liquidity,
                raw_json=excluded.raw_json,
                updated_at=excluded.updated_at,
                resolved=excluded.resolved,
                winning_outcome=excluded.winning_outcome,
                resolved_at=excluded.resolved_at
            """,
            (
                condition_id,
                question,
                slug,
                volume,
                liquidity,
                json.dumps(market),
                now,
                now,
                1 if winning_outcome else 0,
                winning_outcome,
                now if winning_outcome else None,
            ),
        )

        saved_markets += 1

        if not winning_outcome:
            skipped += 1
            continue

        cur.execute(
            """
            UPDATE trades
            SET
                resolved = 1,
                won = CASE
                    WHEN side = 'BUY' AND outcome = ? THEN 1
                    WHEN side = 'SELL' AND outcome != ? THEN 1
                    ELSE 0
                END,
                resolved_at = ?
            WHERE condition_id = ?
            """,
            (
                winning_outcome,
                winning_outcome,
                now,
                condition_id,
            ),
        )

        resolved_trades += cur.rowcount

    conn.commit()
    conn.close()

    return {
        "closed_markets_checked": len(closed_markets),
        "saved_markets": saved_markets,
        "resolved_trades": resolved_trades,
        "skipped": skipped,
        "timestamp": now,
    }


def get_resolved_markets(limit: int = 25):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            condition_id,
            question,
            slug,
            winning_outcome,
            resolved_at,
            volume,
            liquidity
        FROM markets
        WHERE resolved = 1
        ORDER BY resolved_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows