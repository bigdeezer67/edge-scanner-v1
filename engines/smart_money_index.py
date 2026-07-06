import time

from core.database import get_connection
from engines.early_entry import calculate_early_entry_scores


def calculate_smart_money_index(limit: int = 50):
    early_entries = calculate_early_entry_scores(limit=500)["entries"]

    wallet_alpha = {}

    for entry in early_entries:
        wallet = entry["wallet_address"]

        if wallet not in wallet_alpha:
            wallet_alpha[wallet] = {
                "scores": [],
                "wins": 0,
                "total": 0,
            }

        wallet_alpha[wallet]["scores"].append(entry["early_alpha_score"])
        wallet_alpha[wallet]["wins"] += 1 if entry["won"] == 1 else 0
        wallet_alpha[wallet]["total"] += 1

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
            first_seen,
            last_seen
        FROM wallets
        ORDER BY score DESC, total_trades DESC
        """
    )

    wallets = [dict(row) for row in cur.fetchall()]
    conn.close()

    indexed_wallets = []

    for wallet in wallets:
        address = wallet["wallet_address"]
        alpha_data = wallet_alpha.get(address)

        if alpha_data:
            alpha_timing = sum(alpha_data["scores"]) / len(alpha_data["scores"])
            conviction_accuracy = (alpha_data["wins"] / alpha_data["total"]) * 100
        else:
            alpha_timing = 0
            conviction_accuracy = 0

        profitability = _clamp(50 + (wallet["roi"] or 0))
        consistency = _calculate_consistency(wallet)

        smart_money_score = (
            alpha_timing * 0.30
            + conviction_accuracy * 0.25
            + (wallet["score"] or 0) * 0.25
            + profitability * 0.10
            + consistency * 0.10
        )

        indexed_wallets.append(
            {
                "wallet_address": address,
                "total_trades": wallet["total_trades"],
                "wins": wallet["wins"],
                "losses": wallet["losses"],
                "win_rate": wallet["win_rate"],
                "roi": wallet["roi"],
                "nexora_rating": wallet["score"],
                "alpha_timing": round(alpha_timing, 2),
                "conviction_accuracy": round(conviction_accuracy, 2),
                "profitability": round(profitability, 2),
                "consistency": round(consistency, 2),
                "smart_money_score": round(smart_money_score, 2),
                "level": _smart_money_level(smart_money_score),
                "first_seen": wallet["first_seen"],
                "last_seen": wallet["last_seen"],
            }
        )

    indexed_wallets = sorted(
        indexed_wallets,
        key=lambda x: x["smart_money_score"],
        reverse=True,
    )[:limit]

    return {
        "status": "ok",
        "wallets_found": len(indexed_wallets),
        "wallets": indexed_wallets,
        "timestamp": int(time.time()),
    }


def _calculate_consistency(wallet):
    total = wallet["wins"] + wallet["losses"]

    if total <= 0:
        return 0

    win_rate = wallet["win_rate"] or 0
    trade_depth = min((wallet["total_trades"] or 0) / 250, 1) * 100

    return _clamp((win_rate * 0.65) + (trade_depth * 0.35))


def _smart_money_level(score):
    if score >= 85:
        return "ELITE"
    if score >= 70:
        return "HIGH"
    if score >= 50:
        return "PROMISING"
    if score >= 30:
        return "WATCHLIST"
    return "UNPROVEN"


def _clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))