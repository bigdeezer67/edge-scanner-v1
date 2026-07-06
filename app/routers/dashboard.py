from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from core.database import db_stats
from core.wallets import get_top_wallets
from analysis.outcomes import get_resolved_markets
from analysis.conviction import calculate_conviction

from app.services.market_cache import CACHE, refresh_markets
from app.templates.dashboard import render_dashboard

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home():
    refresh_markets()

    stats = db_stats()
    conviction = calculate_conviction(
        window_seconds=900,
        min_wallets=2,
        min_avg_score=10,
        limit=10,
    )

    html = render_dashboard(
        stats=stats,
        cache=CACHE,
        conviction=conviction,
        markets=CACHE["markets"],
        wallets=get_top_wallets(limit=10),
        resolved_markets=get_resolved_markets(limit=10),
    )

    return HTMLResponse(html)