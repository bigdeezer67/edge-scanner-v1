import asyncio
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from core.database import init_db, db_stats
from core.gamma import get_active_markets
from core.collector import save_markets, save_trades
from core.wallets import get_top_wallets, get_wallet_profile
from analysis.outcomes import save_resolved_markets, get_resolved_markets

app = FastAPI(title="Nexora")

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


async def market_collector_loop():
    await asyncio.sleep(5)

    while True:
        try:
            result = save_markets(limit=50)
            print(f"market collector tick: {result}")
        except Exception as e:
            print(f"market_collector_loop error: {e}")

        await asyncio.sleep(60)


async def trade_collector_loop():
    await asyncio.sleep(10)

    while True:
        try:
            result = save_trades(limit=100)
            print(f"trade collector tick: {result}")
        except Exception as e:
            print(f"trade_collector_loop error: {e}")

        await asyncio.sleep(30)


async def outcome_collector_loop():
    await asyncio.sleep(20)

    while True:
        try:
            result = save_resolved_markets(limit=100)
            print(f"outcome collector tick: {result}")
        except Exception as e:
            print(f"outcome_collector_loop error: {e}")

        await asyncio.sleep(300)


@app.on_event("startup")
async def startup():
    init_db()
    refresh_markets()
    asyncio.create_task(market_collector_loop())
    asyncio.create_task(trade_collector_loop())
    asyncio.create_task(outcome_collector_loop())


@app.get("/", response_class=HTMLResponse)
def home():
    refresh_markets()

    market_rows = ""

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

        market_rows += f"""
        <tr>
            <td>{question_html}</td>
            <td>{volume}</td>
            <td>{liquidity}</td>
        </tr>
        """

    wallet_rows = ""

    for wallet in get_top_wallets(limit=10):
        address = wallet["wallet_address"]
        short_address = f"{address[:6]}...{address[-4:]}"
        wallet_rows += f"""
        <tr>
            <td><a href="/api/wallets/{address}" target="_blank">{short_address}</a></td>
            <td>{wallet["total_trades"]}</td>
            <td>{round(wallet["avg_size"], 2)}</td>
            <td>{wallet["unique_markets"]}</td>
        </tr>
        """

    resolved_rows = ""

    for market in get_resolved_markets(limit=10):
        slug = market.get("slug") or ""
        question = market.get("question") or "Unknown Market"
        winning_outcome = market.get("winning_outcome") or "Unknown"

        if slug:
            link = f"https://polymarket.com/event/{slug}"
            question_html = f'<a href="{link}" target="_blank">{question}</a>'
        else:
            question_html = question

        resolved_rows += f"""
        <tr>
            <td>{question_html}</td>
            <td>{winning_outcome}</td>
            <td>{market.get("volume")}</td>
        </tr>
        """

    error_html = ""
    if CACHE["error"]:
        error_html = f"""
        <div class="error">
            {CACHE["error"]}
        </div>
        """

    stats = db_stats()

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Nexora</title>

<style>
body {{
    background:#0d1117;
    color:white;
    font-family:Arial;
    padding:30px;
}}

h1 {{
    margin-bottom:4px;
}}

.sub {{
    color:#9aa8b6;
    margin-bottom:28px;
}}

.grid {{
    display:grid;
    grid-template-columns: repeat(7, 1fr);
    gap:14px;
    margin-bottom:30px;
}}

.card {{
    background:#111827;
    border:1px solid #263241;
    border-radius:10px;
    padding:16px;
}}

.card .label {{
    color:#9aa8b6;
    font-size:13px;
}}

.card .value {{
    font-size:24px;
    font-weight:bold;
    margin-top:6px;
}}

.section {{
    margin-top:34px;
}}

table {{
    width:100%;
    border-collapse:collapse;
    background:#111827;
}}

th,td {{
    border-bottom:1px solid #263241;
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

.error {{
    color:#ff6b6b;
    margin-bottom:20px;
}}
</style>

</head>

<body>

<h1>Nexora</h1>
<div class="sub">Predictive market intelligence engine</div>

{error_html}

<div class="grid">
    <div class="card">
        <div class="label">Markets</div>
        <div class="value">{stats["markets"]}</div>
    </div>
    <div class="card">
        <div class="label">Snapshots</div>
        <div class="value">{stats["market_snapshots"]}</div>
    </div>
    <div class="card">
        <div class="label">Wallets</div>
        <div class="value">{stats["wallets"]}</div>
    </div>
    <div class="card">
        <div class="label">Trades</div>
        <div class="value">{stats["trades"]}</div>
    </div>
    <div class="card">
        <div class="label">Resolved Markets</div>
        <div class="value">{stats["resolved_markets"]}</div>
    </div>
    <div class="card">
        <div class="label">Resolved Trades</div>
        <div class="value">{stats["resolved_trades"]}</div>
    </div>
    <div class="card">
        <div class="label">Signals</div>
        <div class="value">{stats["signals"]}</div>
    </div>
</div>

<div class="section">
<h2>Top Wallets</h2>

<table>
<thead>
<tr>
<th>Wallet</th>
<th>Total Trades</th>
<th>Avg Size</th>
<th>Unique Markets</th>
</tr>
</thead>
<tbody>
{wallet_rows}
</tbody>
</table>
</div>

<div class="section">
<h2>Resolved Markets</h2>

<table>
<thead>
<tr>
<th>Market</th>
<th>Winning Outcome</th>
<th>Volume</th>
</tr>
</thead>
<tbody>
{resolved_rows}
</tbody>
</table>
</div>

<div class="section">
<h2>Live Polymarket Markets</h2>

<table>
<thead>
<tr>
<th>Market</th>
<th>Volume</th>
<th>Liquidity</th>
</tr>
</thead>
<tbody>
{market_rows}
</tbody>
</table>
</div>

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


@app.get("/api/collect-trades")
def api_collect_trades():
    result = save_trades(limit=100)

    return {
        "status": "ok",
        "result": result,
        "db": db_stats(),
    }


@app.get("/api/outcomes")
def api_outcomes():
    result = save_resolved_markets(limit=100)

    return {
        "status": "ok",
        "result": result,
        "db": db_stats(),
    }


@app.get("/api/resolved-markets")
def api_resolved_markets():
    return {
        "markets": get_resolved_markets(limit=25),
        "db": db_stats(),
    }


@app.get("/api/wallets")
def api_wallets():
    return {
        "wallets": get_top_wallets(limit=25),
        "db": db_stats(),
    }


@app.get("/api/wallets/{wallet_address}")
def api_wallet_profile(wallet_address: str):
    profile = get_wallet_profile(wallet_address)

    if not profile:
        return {
            "status": "not_found",
            "wallet": wallet_address,
        }

    return {
        "status": "ok",
        "profile": profile,
    }


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