from core.database import init_db
from app.services.market_cache import refresh_markets
from app.services.scheduler import start_background_tasks


async def startup_event():
    init_db()
    refresh_markets()
    start_background_tasks()