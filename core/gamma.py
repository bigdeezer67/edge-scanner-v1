import requests

GAMMA_BASE = "https://gamma-api.polymarket.com"


def get_active_markets(limit: int = 50):
    url = f"{GAMMA_BASE}/markets"

    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "volume",
        "ascending": "false",
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()