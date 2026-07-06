import asyncio
import time

from engines.signal_engine import run_signal_engine


SIGNAL_ENGINE_STATUS = {
    "enabled": True,
    "running": False,
    "last_run": None,
    "last_duration_ms": None,
    "processed": 0,
    "created": 0,
    "updated": 0,
    "errors": 0,
    "last_error": None,
}


async def signal_engine_loop():
    await asyncio.sleep(45)

    while True:
        start = time.time()
        SIGNAL_ENGINE_STATUS["running"] = True

        try:
            result = run_signal_engine(
                window_seconds=900,
                min_wallets=2,
                min_avg_score=10,
                limit=25,
            )

            processed_signals = result.get("signals", [])
            created = sum(1 for signal in processed_signals if signal.get("action") == "created")
            updated = sum(1 for signal in processed_signals if signal.get("action") == "updated")

            SIGNAL_ENGINE_STATUS["processed"] = result.get("processed_signals", 0)
            SIGNAL_ENGINE_STATUS["created"] = created
            SIGNAL_ENGINE_STATUS["updated"] = updated
            SIGNAL_ENGINE_STATUS["last_error"] = None

            print(f"signal engine tick: {result}")

        except Exception as e:
            SIGNAL_ENGINE_STATUS["errors"] += 1
            SIGNAL_ENGINE_STATUS["last_error"] = str(e)
            print(f"signal_engine_loop error: {e}")

        finally:
            SIGNAL_ENGINE_STATUS["running"] = False
            SIGNAL_ENGINE_STATUS["last_run"] = int(time.time())
            SIGNAL_ENGINE_STATUS["last_duration_ms"] = int((time.time() - start) * 1000)

        await asyncio.sleep(60)


def start_signal_scheduler():
    asyncio.create_task(signal_engine_loop())


def get_signal_engine_status():
    return SIGNAL_ENGINE_STATUS