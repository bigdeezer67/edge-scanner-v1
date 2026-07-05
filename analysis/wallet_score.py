import time

from core.database import get_connection


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def calculate_experience_score(total_trades):
    if total_trades <= 0:
        return 0

    return clamp((total_trades / 500) * 100)


def calculate_win_rate_score(win_rate):
    if win_rate <= 0:
        return 0

    return clamp(win_rate)


def calculate_roi_score(roi):
    return clamp(50 + roi)


def calculate_activity_score(last_seen):
    if not last_seen:
        return 0

    now = int(time.time())
    age_seconds = now - int(last_seen)

    if age_seconds <= 3600:
        return 100

    if age_seconds >= 604800:
        return 0

    return clamp(100 - ((age_seconds / 604800) * 100))


def calculate_wallet_score(total_trades, win_rate, roi, last_seen):
    experience_score = calculate_experience_score(total_trades)
    win_rate_score = calculate_win_rate_score(win_rate)
    roi_score = calculate_roi_score(roi)
    activity_score = calculate_activity_score(last_seen)

    score = (
        experience_score * 0.25
        + win_rate_score * 0.35
        + roi_score * 0.25
        + activity_score * 0.15
    )

    return {
        "experience_score": round(experience_score, 2),
        "win_rate_score": round(win_rate_score, 2),
        "roi_score": round(roi_score, 2),
        "activity_score": round(activity_score, 2),
        "nexora_score": round(score, 2),
    }


def update_wallet_scores():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            wallet_address,
            total_trades,
            win_rate,
            roi,
            last_seen
        FROM wallets
        """
    )

    wallets = cur.fetchall()
    updated = 0

    for wallet in wallets:
        score_data = calculate_wallet_score(
            total_trades=wallet["total_trades"] or 0,
            win_rate=wallet["win_rate"] or 0,
            roi=wallet["roi"] or 0,
            last_seen=wallet["last_seen"],
        )

        cur.execute(
            """
            UPDATE wallets
            SET score = ?
            WHERE wallet_address = ?
            """,
            (
                score_data["nexora_score"],
                wallet["wallet_address"],
            ),
        )

        updated += 1

    conn.commit()
    conn.close()

    return {
        "updated_wallets": updated,
        "timestamp": int(time.time()),
    }


def score_preview(limit=25):
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
        ORDER BY score DESC, total_trades DESC
        LIMIT ?
        """,
        (limit,),
    )

    wallets = [dict(row) for row in cur.fetchall()]
    conn.close()

    return wallets
