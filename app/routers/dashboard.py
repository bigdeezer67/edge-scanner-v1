from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from engines.signal_engine import (
    get_live_signals,
    get_signal_history,
    get_recent_signal_events,
)

from engines.signal_engine import get_signal_wallets
from core.database import db_stats
from core.wallets import get_top_wallets, get_wallet_profile
from analysis.outcomes import get_resolved_markets
from app.services.market_cache import CACHE, refresh_markets

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(request: Request):
    refresh_markets()

    stats = db_stats()
    live = get_live_signals(limit=10)
    recent_events = get_recent_signal_events(limit=8)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "signals": live["signals"],
            "signal_count": live["signals_found"],
            "recent_events": recent_events["events"],
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
    recent_events = get_recent_signal_events(limit=10)

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
        "activity": recent_events["events"],
    }


@router.get("/signals/{signal_uuid}")
def signal_detail(request: Request, signal_uuid: str):
    history = get_signal_history(signal_uuid)
    wallets = get_signal_wallets(signal_uuid, limit=12)

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
                    "side": "N/A",
                    "avg_entry": 0,
                    "total_size": 0,
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
            "signal_wallets": wallets["wallets"],
        },
    )

@router.get("/wallets/{wallet_address}")
def wallet_detail(request: Request, wallet_address: str):
    profile = get_wallet_profile(wallet_address)

    if not profile:
        wallet = {
            "wallet_address": wallet_address,
            "score": 0,
            "win_rate": 0,
            "roi": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "first_seen": "-",
            "last_seen": "-",
            "avg_price": 0,
            "avg_size": 0,
            "total_size": 0,
            "unique_markets": 0,
        }

        return templates.TemplateResponse(
            "wallet_detail.html",
            {
                "request": request,
                "wallet": wallet,
                "recent_trades": [],
                "favorite_markets": [],
                "signals": [],
            },
        )

    return templates.TemplateResponse(
        "wallet_detail.html",
        {
            "request": request,
            "wallet": profile["wallet"],
            "recent_trades": profile["recent_trades"],
            "favorite_markets": profile["favorite_markets"],
            "signals": [],
        },
    )