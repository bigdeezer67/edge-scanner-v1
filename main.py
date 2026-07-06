from fastapi import FastAPI

from core.database import db_stats
from app.services.market_cache import CACHE
from app.services.startup import startup_event

from app.routers.dashboard import router as dashboard_router
from app.routers.markets import router as markets_router
from app.routers.wallets import router as wallets_router
from app.routers.intelligence import router as intelligence_router
from app.routers.system import router as system_router

app = FastAPI(title="Nexora")

app.include_router(dashboard_router)
app.include_router(markets_router)
app.include_router(wallets_router)
app.include_router(intelligence_router)
app.include_router(system_router)


@app.on_event("startup")
async def startup():
    await startup_event()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "Nexora",
        "markets_loaded": len(CACHE["markets"]),
        "last_updated": CACHE["last_updated"],
        "error": CACHE["error"],
        "db": db_stats(),
    }