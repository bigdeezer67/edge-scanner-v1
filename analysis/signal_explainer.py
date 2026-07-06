from analysis.conviction import calculate_conviction


def explain_signals(
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

    explained = []

    for signal in conviction["signals"]:
        explained.append(
            {
                **signal,
                "explanation": build_signal_explanation(signal),
            }
        )

    return {
        "window_seconds": window_seconds,
        "signals_found": len(explained),
        "signals": explained,
        "timestamp": conviction["timestamp"],
    }


def build_signal_explanation(signal):
    parts = []

    parts.append(
        f"{signal['wallet_count']} tracked wallets bought {signal['outcome']}."
    )

    parts.append(
        f"Their average Nexora Rating is {signal['avg_wallet_score']}."
    )

    parts.append(
        f"Combined buy size is {signal['total_size']}."
    )

    parts.append(
        f"Convergence score is {signal['convergence_score']}, "
        f"pressure score is {signal['pressure_score']}, "
        f"and final conviction is {signal['conviction_score']}."
    )

    opposition = signal.get("opposition")

    if opposition and opposition.get("opposition_level") != "NONE":
        parts.append(
            f"Opposition detected: {opposition['opposing_outcome']} has "
            f"{opposition['opposition_level'].lower()} counter-pressure."
        )
    else:
        parts.append("No major smart-wallet opposition detected.")

    parts.append(
        f"Signal level: {signal['conviction_level']}."
    )

    return " ".join(parts)