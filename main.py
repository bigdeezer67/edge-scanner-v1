import os
import time
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Edge Scanner v1")

GAMMA_BASE = "https://gamma-api.polymarket.com"

CACHE = {
    "markets": [],
    "last_updated": None,
    "error": None,
}


def fetch_active_markets(limit: int = 25):
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


def refresh_markets():
    try:
        markets = fetch_active_markets()
        CACHE["markets"] = markets
        CACHE["last_updated"] = int(time.time())
        CACHE["error"] = None
    except Exception as e:
        CACHE["error"] = str(e)


@app.on_event("startup")
def startup():
    refresh_markets()


@app.get("/")
def home():
    refresh_markets()

    rows = ""

    for market in CACHE["markets"][:25]:
        question = market.get("question", "Unknown market")
        volume = market.get("volume", "N/A")
        liquidity = market.get("liquidity", "N/A")
        slug = market.get("slug", "")
        url = f"https://polymarket.com/event/{slug}" if slug else "#"

        rows += f"""
        <tr>
            <td><a href="{url}" target="_blank">{question}</a></td>
            <td>{volume}</td>
            <td>{liquidity}</td>
        </tr>
        """

    error_block = f"<p class='error'>{CACHE['error']}</p>" if CACHE["error"] else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Edge Scanner v1</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #0b0f14;
                color: #e8eef5;
                padding: 24px;
            }}
            h1 {{
                margin-bottom: 4px;
            }}
            .sub {{
                color: #9aa8b6;
                margin-bottom: 24px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: #111821;
            }}
            th, td {{
                padding: 12px;
                border-bottom: 1px solid #263241;
                text-align: left;
                vertical-align: top;
            }}
            th {{
                color: #9fd3ff;
            }}
            a {{
                color: #7cc7ff;
                text-decoration: none;
            }}
            .error {{
                color: #ff6b6b;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Edge Scanner v1</h1>
        <div class="sub">Polymarket active market feed. Paper mode only.</div>
        {error_block}
        <table>
            <thead>
                <tr>
                    <th>Market</th>
                    <th>Volume</th>
                    <th>Liquidity</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """

    return HTMLResponse(html)


@app.get("/api/markets")
def api_markets():
    refresh_markets()
    return JSONResponse(CACHE)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "markets_loaded": len(CACHE["markets"]),
        "last_updated": CACHE["last_updated"],
        "error": CACHE["error"], 