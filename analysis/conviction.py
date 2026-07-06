import time

from analysis.convergence import detect_convergence
from analysis.market_pressure import calculate_market_pressure
from analysis.opposition import detect_opposition


def calculate_conviction(
    window_seconds: int = 900,
    min_wallets: int = 2,
    min_avg_score: float = 10,
    limit: int = 25,
):
    now = int(time.time())

    convergence = detect_convergence(
        window_seconds=window_seconds,
        min_wallets=min_wallets,
        min_avg_score=min_avg_score,
        limit=limit,
    )

    pressure = calculate_market_pressure(
        window_seconds=window_seconds,
        limit=limit * 3,
    )

    opposition = detect_opposition(
        window_seconds=window_seconds,
        min_wallet_score=min_avg_score,
        limit=limit * 3,
    )

    pressure_lookup = {
        (item["condition_id"], item["outcome"]): item
        for item in pressure["markets"]
    }

    opposition_lookup = {
        item["condition_id"]: item
        for item in opposition["conflicts"]
    }

    conviction_signals = []

    for signal in convergence["signals"]:
        key = (signal["condition_id"], signal["outcome"])
        pressure_data = pressure_lookup.get(key)
        opposition_data = opposition_lookup.get(signal["condition_id"])

        convergence_score = signal.get("signal_strength") or 0
        pressure_score = pressure_data.get("pressure_score") if pressure_data else 0
        opposition_penalty = _opposition_penalty(
            signal=signal,
            opposition_data=opposition_data,
        )

        conviction_score = (
            convergence_score * 0.45
            + pressure_score * 0.40
            - opposition_penalty
        )

        conviction_score = max(0, min(100, conviction_score))

        conviction_signals.append(
            {
                "condition_id": signal["condition_id"],
                "market_slug": signal["market_slug"],
                "outcome": signal["outcome"],
                "side": signal["side"],
                "wallet_count": signal["wallet_count"],
                "avg_wallet_score": signal["avg_wallet_score"],
                "total_size": signal["total_size"],
                "avg_entry": signal["avg_entry"],
                "convergence_score": round(convergence_score, 2),
                "pressure_score": round(pressure_score, 2),
                "opposition_penalty": round(opposition_penalty, 2),
                "conviction_score": round(conviction_score, 2),
                "conviction_level": _conviction_level(conviction_score),
                "pressure": pressure_data,
                "opposition": opposition_data,
                "wallets": signal.get("wallets", []),
            }
        )

    conviction_signals = sorted(
        conviction_signals,
        key=lambda x: x["conviction_score"],
        reverse=True,
    )[:limit]

    return {
        "window_seconds": window_seconds,
        "signals_found": len(conviction_signals),
        "signals": conviction_signals,
        "timestamp": now,
    }


def _opposition_penalty(signal, opposition_data):
    if not opposition_data:
        return 0

    if opposition_data.get("leading_outcome") == signal.get("outcome"):
        return (opposition_data.get("opposition_ratio") or 0) * 20

    return (opposition_data.get("opposition_ratio") or 0) * 35


def _conviction_level(score: float):
    if score >= 80:
        return "ELITE"
    if score >= 65:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    if score >= 25:
        return "LOW"
    return "WEAK"