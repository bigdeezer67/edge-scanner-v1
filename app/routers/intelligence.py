from fastapi import APIRouter

from analysis.convergence import detect_convergence
from analysis.market_pressure import calculate_market_pressure
from analysis.opposition import detect_opposition
from analysis.conviction import calculate_conviction
from analysis.signal_explainer import explain_signals

from engines.early_entry import calculate_early_entry_scores
from engines.smart_money_index import calculate_smart_money_index
from engines.market_timeline import get_market_timeline
from engines.signal_engine import (
    run_signal_engine,
    get_live_signals,
    get_signal_history,
    get_signal_by_uuid,
    get_top_signals,
    get_trending_signals,
)

router = APIRouter()


@router.get("/api/convergence")
def api_convergence():
    return detect_convergence(
        window_seconds=900,
        min_wallets=2,
        min_avg_score=10,
        limit=25,
    )


@router.get("/api/market-pressure")
def api_market_pressure():
    return calculate_market_pressure(
        window_seconds=900,
        min_total_size=0,
        limit=25,
    )


@router.get("/api/opposition")
def api_opposition():
    return detect_opposition(
        window_seconds=900,
        min_wallet_score=10,
        limit=25,
    )


@router.get("/api/conviction")
def api_conviction():
    return calculate_conviction(
        window_seconds=900,
        min_wallets=2,
        min_avg_score=10,
        limit=25,
    )


@router.get("/api/signals/explained")
def api_explained_signals():
    return explain_signals(
        window_seconds=900,
        min_wallets=2,
        min_avg_score=10,
        limit=25,
    )


@router.get("/api/early-entry")
def api_early_entry():
    return calculate_early_entry_scores(limit=50)


@router.get("/api/smart-money")
def api_smart_money():
    return calculate_smart_money_index(limit=50)


@router.get("/api/market-timeline/{condition_id}")
def api_market_timeline(condition_id: str):
    return get_market_timeline(condition_id=condition_id, limit=100)


@router.get("/api/signals/run")
def api_run_signal_engine():
    return run_signal_engine(
        window_seconds=900,
        min_wallets=2,
        min_avg_score=10,
        limit=25,
    )

@router.get("/api/signals/live")
def api_live_signals():
    return get_live_signals(limit=50)


@router.get("/api/signals/{signal_uuid}/history")
def api_signal_history(signal_uuid: str):
    return get_signal_history(signal_uuid=signal_uuid)

@router.get("/api/signals/top")
def api_top_signals():
    return get_top_signals(limit=25)


@router.get("/api/signals/trending")
def api_trending_signals():
    return get_trending_signals(limit=25)


@router.get("/api/signals/{signal_uuid}")
def api_signal_by_uuid(signal_uuid: str):
    return get_signal_by_uuid(signal_uuid=signal_uuid)
    