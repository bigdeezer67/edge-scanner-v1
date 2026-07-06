from core.database import init_db
from app.services.market_cache import refresh_markets
from app.services.scheduler import start_background_tasks
from app.services.signal_scheduler import start_signal_scheduler


async def startup_event():
    init_db()
    refresh_markets()

    start_background_tasks()
    start_signal_scheduler()