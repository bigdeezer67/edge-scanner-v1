import asyncio
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from core.database import init_db, db_stats
from core.gamma import get_active_markets
from core.collector import save_markets

app = FastAPI(title="Edge Scanner v1")

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


async def collector_loop():
    await asyncio.sleep(5)

    while True:
        try:
            result = save_markets(limit=50)
            print(f"market collector tick: {result}")
        except Exception as e:
            print(f"collector_loop error: {e}")

        await asyncio.sleep(60)


@app.on_event("startup")
async def startup():
    init_db()
    refresh_markets()
    asyncio.create_task(collector_loop())


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


@app.get("/api/db")
def api_db():
    return db_stats()


@app.get("/api/collect")
def api_collect():
    result = save_markets(limit=50)

    return {
        "status": "ok",
        "result": result,
        "db": db_stats(),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "markets_loaded": len(CACHE["markets"]),
        "last_updated": CACHE["last_updated"],
        "error": CACHE["error"],
        "db": db_stats(),
    }