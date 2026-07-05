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
        CACHE["markets"] = fetch_active_markets()
        CACHE["last_updated"] = int(time.time())
        CACHE["error"] = None
    except Exception as e:
        CACHE["error"] = str(e)


@app.on_event("startup")
def startup():
    refresh_markets()


@app.get("/", response_class=HTMLResponse)
def home():
    refresh_markets()

    rows = ""

    for market in CACHE["markets"][:25]:
        question = market.get("question", "Unknown Market")
        volume = market.get("volume", "N/A")
        liquidity = market.get("liquidity", "N/A")
        slug = market.get("slug", "")

        if slug:
            link = f"https://polymarket.com/event/{slug}"
            question_html = f'<a href="{link}" target="_blank">{question}</a>'
        else:
            question_html = question

        rows += f"""
        <tr>
            <td>{question_html}</td>
            <td>{volume}</td>
            <td>{liquidity}</td>
        </tr>
        """

    error_html = ""
    if CACHE["error"]:
        error_html = f"""
        <div style="color:#ff6b6b;margin-bottom:20px;">
            {CACHE["error"]}
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Edge Scanner v1</title>
<style>
body {{
    background:#0d1117;
    color:white;
    font-family:Arial;
    padding:30px;
}}
table {{
    width:100%;
    border-collapse:collapse;
}}
th,td {{
    border-bottom:1px solid #333;
    padding:12px;
    text-align:left;
}}
th {{
    color:#4db8ff;
}}
a {{
    color:#66ccff;
    text-decoration:none;
}}
</style>
</head>
<body>
<h1>Edge Scanner v1</h1>
<p>Live Polymarket Active Markets</p>
{error_html}
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
    return JSONResponse(
        {
            "markets": CACHE["markets"],
            "last_updated": CACHE["last_updated"],
            "error": CACHE["error"],
        }
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "markets_loaded": len(CACHE["markets"]),
        "last_updated": CACHE["last_updated"],
        "error": CACHE["error"],
    }
