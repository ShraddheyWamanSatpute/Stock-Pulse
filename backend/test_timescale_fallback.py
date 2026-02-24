import sys
import asyncio
import logging
from services.timeseries_store import init_timeseries_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_timescale_fallback():
    # Initialize the time-series store
    store = await init_timeseries_store()
    
    # Attempt to fetch weekly prices
    logger.info("Testing get_weekly_prices (should gracefully log warning and return empty list if TimescaleDB not installed)")
    weekly_prices = await store.get_weekly_prices("RELIANCE")
    
    logger.info(f"Result: {weekly_prices}")
    
    if len(weekly_prices) == 0:
        logger.info("✅ Fallback successful: returned empty list instead of crashing")
    else:
        logger.info("ℹ️ Returned data (TimescaleDB must be installed and populated!)")
        
    await store.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_timescale_fallback())
