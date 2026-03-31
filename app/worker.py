# --- worker.py ---
import asyncio
from app.core.logger import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.api.offers.service import OfferService


async def main():
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    scheduler.add_job(
        OfferService.run_cleanup,
        'interval',
        hours=2,
        id='cleanup_task',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("--- Background Worker Started ---")
    logger.info("Task 'cleanup_task' scheduled every 2 hours.")
    
    try:
        # Используем Event вместо бесконечного цикла со sleep
        # Это более "нативный" способ держать асинхронный процесс запущенным
        stop_event = asyncio.Event()
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping worker...")
    finally:
        scheduler.shutdown()
        logger.info("Worker stopped successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass