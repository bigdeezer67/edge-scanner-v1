from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.database import db_stats
from core.gamma import get_active_markets
from core.collector import save_markets, save_trades
from analysis.outcomes import save_resolved_markets, get_resolved_markets
from app.services.market_cache import refresh_markets, CACHE
from fastapi import Request
from fastapi.templating import Jinja2Templates
from core.database import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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

@router.get("/markets/{condition_id}")
def market_detail(request: Request, condition_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM markets
        WHERE condition_id = ?
        """,
        (condition_id,),
    )

    market = cur.fetchone()

    cur.execute(
        """
        SELECT *
        FROM signals
        WHERE condition_id = ?
        ORDER BY updated_at DESC
        LIMIT 25
        """,
        (condition_id,),
    )

    signals = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        SELECT *
        FROM trades
        WHERE condition_id = ?
        ORDER BY timestamp DESC
        LIMIT 50
        """,
        (condition_id,),
    )

    trades = [dict(row) for row in cur.fetchall()]

    conn.close()

    if market:
        market_data = dict(market)
    elif signals:
        first_signal = signals[0]

        market_data = {
            "condition_id": condition_id,
            "question": first_signal.get("market_slug"),
            "slug": first_signal.get("market_slug"),
            "active": 1,
            "closed": 0,
            "volume": 0,
            "liquidity": 0,
            "resolved": 0,
            "winning_outcome": None,
            "resolved_at": None,
        }
    else:
        return {"detail": "Market not found"}

    return templates.TemplateResponse(
        "market_detail.html",
        {
            "request": request,
            "market": market_data,
            "signals": signals,
            "trades": trades,
        },
    )
