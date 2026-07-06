from fastapi import APIRouter

from core.database import db_stats

router = APIRouter()


@router.get("/api/db")
def api_db():
    return db_stats()