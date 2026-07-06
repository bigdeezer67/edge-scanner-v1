import asyncio

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from core.database import init_db, db_stats
from core.collector import save_markets, save_trades
from core.wallets import get_top_wallets
from analysis.outcomes import save_resolved_markets, get_resolved_markets
from analysis.wallet_score import update_wallet_scores
from analysis.wallet_stats import update_wallet_stats
from analysis.conviction import calculate_conviction

from app.services.market_cache import CACHE, refresh_markets
from app.routers.markets import router as markets_router
from app.routers.wallets import router as wallets_router
from app.routers.intelligence import router as intelligence_router
from app.routers.system import router as system_router

app = FastAPI(title="Nexora")

app.include_router(markets_router)
app.include_router(wallets_router)
app.include_router(intelligence_router)
app.include_router(system_router)


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


async def wallet_intelligence_loop():
    await asyncio.sleep(35)

    while True:
        try:
            stats_result = update_wallet_stats()
            score_result = update_wallet_scores()
            print(f"wallet stats tick: {stats_result}")
            print(f"wallet score tick: {score_result}")
        except Exception as e:
            print(f"wallet_intelligence_loop error: {e}")

        await asyncio.sleep(120)


@app.on_event("startup")
async def startup():
    init_db()
    refresh_markets()
    asyncio.create_task(market_collector_loop())
    asyncio.create_task(trade_collector_loop())
    asyncio.create_task(outcome_collector_loop())
    asyncio.create_task(wallet_intelligence_loop())


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
            <td>{wallet["win_rate"]}%</td>
            <td>{wallet["roi"]}%</td>
            <td>{round(wallet["score"], 2)}</td>
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

    conviction = calculate_conviction(
        window_seconds=900,
        min_wallets=2,
        min_avg_score=10,
        limit=10,
    )

    signal_rows = ""

    for signal in conviction["signals"]:
        slug = signal.get("market_slug") or ""
        market_name = slug if slug else signal["condition_id"]

        if slug:
            market_html = f'<a href="https://polymarket.com/event/{slug}" target="_blank">{slug}</a>'
        else:
            market_html = market_name

        signal_rows += f"""
        <tr>
            <td>{market_html}</td>
            <td>{signal["outcome"]}</td>
            <td>{signal["wallet_count"]}</td>
            <td>{signal["avg_wallet_score"]}</td>
            <td>{signal["total_size"]}</td>
            <td>{signal["convergence_score"]}</td>
            <td>{signal["pressure_score"]}</td>
            <td>{signal["conviction_score"]}</td>
            <td>{signal["conviction_level"]}</td>
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
        <div class="value">{conviction["signals_found"]}</div>
    </div>
</div>

<div class="section">
<h2>Market Intelligence Signals</h2>

<table>
<thead>
<tr>
<th>Market</th>
<th>Outcome</th>
<th>Wallets</th>
<th>Avg Rating</th>
<th>Total Size</th>
<th>Convergence</th>
<th>Pressure</th>
<th>Conviction</th>
<th>Level</th>
</tr>
</thead>
<tbody>
{signal_rows}
</tbody>
</table>
</div>

<div class="section">
<h2>Top Wallets</h2>

<table>
<thead>
<tr>
<th>Wallet</th>
<th>Total Trades</th>
<th>Win Rate</th>
<th>ROI</th>
<th>Nexora Rating</th>
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