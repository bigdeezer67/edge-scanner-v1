from fastapi import APIRouter

from core.database import db_stats
from app.services.signal_scheduler import get_signal_engine_status

router = APIRouter()


@router.get("/api/db")
def api_db():
    return db_stats()


@router.get("/api/system/signal-engine")
def api_signal_engine_status():
    return get_signal_engine_status()