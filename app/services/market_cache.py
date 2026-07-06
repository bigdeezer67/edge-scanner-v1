import time

from core.gamma import get_active_markets

CACHE = {
    "markets": [],
    "last_updated": None,
    "error": None,
}


def refresh_markets():
    try:
        CACHE["markets"] = get_active_markets(limit=25)
        CACHE["last_updated"] = int(time.time())
        CACHE["error"] = None
    except Exception as e:
        CACHE["error"] = str(e)