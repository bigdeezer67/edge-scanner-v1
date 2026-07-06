from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.database import db_stats
from core.gamma import get_active_markets
from core.collector import save_markets, save_trades
from analysis.outcomes import save_resolved_markets, get_resolved_markets
from app.services.market_cache import refresh_markets, CACHE

router = APIRouter()


@router.get("/api/markets")
def api_markets():
    refresh_markets()

    return JSONResponse(
        {
            "markets": CACHE["markets"],
            "last_updated": CACHE["last_updated"],
            "error": CACHE["error"],
        }
    )


@router.get("/api/collect")
def api_collect():
    result = save_markets(limit=50)

    return {
        "status": "ok",
        "result": result,
        "db": db_stats(),
    }


@router.get("/api/collect-trades")
def api_collect_trades():
    result = save_trades(limit=100)

    return {
        "status": "ok",
        "result": result,
        "db": db_stats(),
    }


@router.get("/api/outcomes")
def api_outcomes():
    result = save_resolved_markets(limit=100)

    return {
        "status": "ok",
        "result": result,
        "db": db_stats(),
    }


@router.get("/api/resolved-markets")
def api_resolved_markets():
    return {
        "markets": get_resolved_markets(limit=25),
        "db": db_stats(),
    }