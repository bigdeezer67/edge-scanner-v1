from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from engines.signal_engine import (
    get_live_signals,
    get_signal_history,
)

from core.database import db_stats
from core.wallets import get_top_wallets

from analysis.outcomes import get_resolved_markets

from app.services.market_cache import CACHE, refresh_markets

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(request: Request):

    refresh_markets()

    stats = db_stats()
    live = get_live_signals(limit=10)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "signals": live["signals"],
            "signal_count": live["signals_found"],
            "markets": CACHE["markets"],
            "wallets": get_top_wallets(limit=10),
            "resolved_markets": get_resolved_markets(limit=10),
            "cache": CACHE,
        },
    )


@router.get("/api/dashboard")
def api_dashboard():

    refresh_markets()

    stats = db_stats()
    live = get_live_signals(limit=25)

    return {
        "metrics": {
            "markets": stats["markets"],
            "trades": stats["trades"],
            "wallets": stats["wallets"],
            "signals": live["signals_found"],
        },
        "signals": live["signals"],
        "wallets": get_top_wallets(limit=10),
        "system": {
            "status": "running",
            "markets_loaded": len(CACHE["markets"]),
            "last_updated": CACHE["last_updated"],
            "cache_error": CACHE["error"],
        },
        "activity": [],
    }


@router.get("/signals/{signal_uuid}")
def signal_detail(request: Request, signal_uuid: str):

    history = get_signal_history(signal_uuid)

    if history["status"] != "ok":
        return templates.TemplateResponse(
            "signal_detail.html",
            {
                "request": request,
                "signal": {
                    "market_slug": "Signal Not Found",
                    "outcome": "Unknown",
                    "status": "NOT_FOUND",
                    "confidence": 0,
                    "pressure_score": 0,
                    "conviction_score": 0,
                    "wallet_count": 0,
                },
                "events": [],
            },
        )

    return templates.TemplateResponse(
        "signal_detail.html",
        {
            "request": request,
            "signal": history["signal"],
            "events": history["events"],
        },
    )