import asyncio

from core.collector import save_markets, save_trades
from analysis.outcomes import save_resolved_markets
from analysis.wallet_score import update_wallet_scores
from analysis.wallet_stats import update_wallet_stats


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


def start_background_tasks():
    asyncio.create_task(market_collector_loop())
    asyncio.create_task(trade_collector_loop())
    asyncio.create_task(outcome_collector_loop())
    asyncio.create_task(wallet_intelligence_loop())