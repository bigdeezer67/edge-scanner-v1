import json
import time
import uuid

from core.database import get_connection
from analysis.conviction import calculate_conviction


ACTIVE_STATUSES = ["NEW", "BUILDING", "CONFIRMED", "STRONG", "WEAKENING"]


def run_signal_engine(
    window_seconds: int = 900,
    min_wallets: int = 2,
    min_avg_score: float = 10,
    limit: int = 25,
):
    conviction = calculate_conviction(
        window_seconds=window_seconds,
        min_wallets=min_wallets,
        min_avg_score=min_avg_score,
        limit=limit,
    )

    processed = []

    for signal in conviction["signals"]:
        processed.append(upsert_signal(signal))

    return {
        "status": "ok",
        "processed_signals": len(processed),
        "signals": processed,
        "timestamp": int(time.time()),
    }


def upsert_signal(signal):
    now = int(time.time())

    condition_id = signal["condition_id"]
    outcome = signal["outcome"]
    side = signal.get("side", "BUY")
    confidence = signal.get("conviction_score") or 0
    new_status = determine_signal_status(confidence)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM signals
        WHERE condition_id = ?
          AND outcome = ?
          AND side = ?
          AND status IN ('NEW', 'BUILDING', 'CONFIRMED', 'STRONG', 'WEAKENING')
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (condition_id, outcome, side),
    )

    existing = cur.fetchone()

    if existing:
        signal_uuid = existing["signal_uuid"]
        old_status = existing["status"]
        old_confidence = existing["confidence"] or 0

        cur.execute(
            """
            UPDATE signals
            SET
                market_slug = ?,
                status = ?,
                confidence = ?,
                conviction_score = ?,
                pressure_score = ?,
                convergence_score = ?,
                opposition_penalty = ?,
                wallet_count = ?,
                avg_wallet_score = ?,
                total_size = ?,
                avg_entry = ?,
                updated_at = ?,
                raw_json = ?
            WHERE signal_uuid = ?
            """,
            (
                signal.get("market_slug"),
                new_status,
                confidence,
                signal.get("conviction_score") or 0,
                signal.get("pressure_score") or 0,
                signal.get("convergence_score") or 0,
                signal.get("opposition_penalty") or 0,
                signal.get("wallet_count") or 0,
                signal.get("avg_wallet_score") or 0,
                signal.get("total_size") or 0,
                signal.get("avg_entry") or 0,
                now,
                json.dumps(signal),
                signal_uuid,
            ),
        )

        event_type = determine_event_type(
            old_status=old_status,
            new_status=new_status,
            old_confidence=old_confidence,
            new_confidence=confidence,
        )

        if event_type:
            insert_signal_event(
                cur=cur,
                signal_uuid=signal_uuid,
                event_type=event_type,
                old_status=old_status,
                new_status=new_status,
                old_confidence=old_confidence,
                new_confidence=confidence,
                details=signal,
                created_at=now,
            )

        action = "updated"

    else:
        signal_uuid = str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO signals (
                signal_uuid,
                condition_id,
                market_slug,
                outcome,
                side,
                status,
                confidence,
                conviction_score,
                pressure_score,
                convergence_score,
                opposition_penalty,
                wallet_count,
                avg_wallet_score,
                total_size,
                avg_entry,
                created_at,
                updated_at,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_uuid,
                condition_id,
                signal.get("market_slug"),
                outcome,
                side,
                new_status,
                confidence,
                signal.get("conviction_score") or 0,
                signal.get("pressure_score") or 0,
                signal.get("convergence_score") or 0,
                signal.get("opposition_penalty") or 0,
                signal.get("wallet_count") or 0,
                signal.get("avg_wallet_score") or 0,
                signal.get("total_size") or 0,
                signal.get("avg_entry") or 0,
                now,
                now,
                json.dumps(signal),
            ),
        )

        insert_signal_event(
            cur=cur,
            signal_uuid=signal_uuid,
            event_type="CREATED",
            old_status=None,
            new_status=new_status,
            old_confidence=None,
            new_confidence=confidence,
            details=signal,
            created_at=now,
        )

        action = "created"

    conn.commit()
    conn.close()

    return {
        "action": action,
        "signal_uuid": signal_uuid,
        "condition_id": condition_id,
        "market_slug": signal.get("market_slug"),
        "outcome": outcome,
        "side": side,
        "status": new_status,
        "confidence": round(confidence, 2),
        "timestamp": now,
    }


def insert_signal_event(
    cur,
    signal_uuid,
    event_type,
    old_status,
    new_status,
    old_confidence,
    new_confidence,
    details,
    created_at,
):
    cur.execute(
        """
        INSERT INTO signal_events (
            signal_uuid,
            event_type,
            old_status,
            new_status,
            old_confidence,
            new_confidence,
            details_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_uuid,
            event_type,
            old_status,
            new_status,
            old_confidence,
            new_confidence,
            json.dumps(details),
            created_at,
        ),
    )


def determine_signal_status(confidence):
    if confidence >= 85:
        return "STRONG"
    if confidence >= 70:
        return "CONFIRMED"
    if confidence >= 45:
        return "BUILDING"
    return "NEW"


def determine_event_type(
    old_status,
    new_status,
    old_confidence,
    new_confidence,
):
    confidence_delta = (new_confidence or 0) - (old_confidence or 0)

    if old_status != new_status:
        return "STATUS_CHANGED"

    if confidence_delta >= 10:
        return "STRENGTHENED"

    if confidence_delta <= -10:
        return "WEAKENED"

    if abs(confidence_delta) >= 3:
        return "CONFIDENCE_UPDATED"

    return None


def get_live_signals(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM signals
        WHERE status IN ('NEW', 'BUILDING', 'CONFIRMED', 'STRONG', 'WEAKENING')
        ORDER BY confidence DESC, updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    signals = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "status": "ok",
        "signals_found": len(signals),
        "signals": signals,
        "timestamp": int(time.time()),
    }


def get_signal_history(signal_uuid: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM signals
        WHERE signal_uuid = ?
        """,
        (signal_uuid,),
    )

    signal = cur.fetchone()

    cur.execute(
        """
        SELECT *
        FROM signal_events
        WHERE signal_uuid = ?
        ORDER BY created_at ASC
        """,
        (signal_uuid,),
    )

    events = [dict(row) for row in cur.fetchall()]
    conn.close()

    if not signal:
        return {
            "status": "not_found",
            "signal_uuid": signal_uuid,
        }

    return {
        "status": "ok",
        "signal": dict(signal),
        "events_found": len(events),
        "events": events,
        "timestamp": int(time.time()),
    }

def get_signal_by_uuid(signal_uuid: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM signals
        WHERE signal_uuid = ?
        """,
        (signal_uuid,),
    )

    signal = cur.fetchone()
    conn.close()

    if not signal:
        return {
            "status": "not_found",
            "signal_uuid": signal_uuid,
        }

    return {
        "status": "ok",
        "signal": dict(signal),
        "timestamp": int(time.time()),
    }


def get_top_signals(limit: int = 25):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM signals
        ORDER BY confidence DESC, updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    signals = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "status": "ok",
        "signals_found": len(signals),
        "signals": signals,
        "timestamp": int(time.time()),
    }


def get_trending_signals(limit: int = 25):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            s.*,
            COUNT(e.id) AS recent_events
        FROM signals s
        LEFT JOIN signal_events e
            ON s.signal_uuid = e.signal_uuid
            AND e.created_at >= ?
        GROUP BY s.signal_uuid
        ORDER BY recent_events DESC, s.confidence DESC, s.updated_at DESC
        LIMIT ?
        """,
        (int(time.time()) - 3600, limit),
    )

    signals = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "status": "ok",
        "signals_found": len(signals),
        "signals": signals,
        "timestamp": int(time.time()),
    }

    ACTIVE_STATUSES = (
    "NEW",
    "BUILDING",
    "CONFIRMED",
    "STRONG",
    "WEAKENING",
)


def expire_old_signals(expire_after_seconds=1800):
    now = int(time.time())
    cutoff = now - expire_after_seconds

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT signal_uuid,status,confidence
        FROM signals
        WHERE status IN ('NEW','BUILDING','CONFIRMED','STRONG','WEAKENING')
        AND updated_at < ?
        """,
        (cutoff,),
    )

    rows = cur.fetchall()

    expired = 0

    for row in rows:

        cur.execute(
            """
            UPDATE signals
            SET
                status='EXPIRED',
                updated_at=?
            WHERE signal_uuid=?
            """,
            (
                now,
                row["signal_uuid"],
            ),
        )

        insert_signal_event(
            cur=cur,
            signal_uuid=row["signal_uuid"],
            event_type="EXPIRED",
            old_status=row["status"],
            new_status="EXPIRED",
            old_confidence=row["confidence"],
            new_confidence=row["confidence"],
            details={},
            created_at=now,
        )

        expired += 1

    conn.commit()
    conn.close()

    return expired

def resolve_finished_markets():
    now = int(time.time())

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            s.signal_uuid,
            s.status,
            s.confidence,
            m.winning_outcome,
            s.outcome
        FROM signals s
        JOIN markets m
            ON s.condition_id=m.condition_id
        WHERE
            m.resolved=1
        AND
            s.status!='RESOLVED'
        """
    )

    rows = cur.fetchall()

    resolved = 0

    for row in rows:

        cur.execute(
            """
            UPDATE signals
            SET
                status='RESOLVED',
                resolved_at=?,
                updated_at=?
            WHERE signal_uuid=?
            """,
            (
                now,
                now,
                row["signal_uuid"],
            ),
        )

        insert_signal_event(
            cur=cur,
            signal_uuid=row["signal_uuid"],
            event_type="RESOLVED",
            old_status=row["status"],
            new_status="RESOLVED",
            old_confidence=row["confidence"],
            new_confidence=row["confidence"],
            details={
                "correct": row["winning_outcome"] == row["outcome"]
            },
            created_at=now,
        )

        resolved += 1

    conn.commit()
    conn.close()

    return resolved