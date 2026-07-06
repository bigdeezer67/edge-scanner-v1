from fastapi import APIRouter

from core.database import db_stats
from core.wallets import get_top_wallets, get_wallet_profile
from analysis.wallet_score import update_wallet_scores, score_preview
from analysis.wallet_stats import update_wallet_stats, wallet_stats_preview

router = APIRouter()


@router.get("/api/wallet-stats")
def api_wallet_stats():
    stats_result = update_wallet_stats()
    score_result = update_wallet_scores()

    return {
        "status": "ok",
        "stats_result": stats_result,
        "score_result": score_result,
        "wallet_stats": wallet_stats_preview(limit=25),
        "db": db_stats(),
    }


@router.get("/api/scores")
def api_scores():
    result = update_wallet_scores()

    return {
        "status": "ok",
        "result": result,
        "top_scores": score_preview(limit=25),
        "db": db_stats(),
    }


@router.get("/api/wallets")
def api_wallets():
    return {
        "wallets": get_top_wallets(limit=25),
        "db": db_stats(),
    }


@router.get("/api/wallets/{wallet_address}")
def api_wallet_profile(wallet_address: str):
    profile = get_wallet_profile(wallet_address)

    if not profile:
        return {
            "status": "not_found",
            "wallet": wallet_address,
        }

    return {
        "status": "ok",
        "profile": profile,
    }