import asyncio
import logging

from fast_api_app.memory_sqlite import update_database

logger = logging.getLogger(__name__)


class BackgroundRunner:
    async def run(self):
        logger.info("Starting background task to update aliases database")
        while True:
            logger.info("Updating aliases database")
            sleep_time = 600
            try:
                update_database()
            except Exception as e:
                logger.error(f"Error updating aliases database: {e}")
                sleep_time = 60

            logger.info("Sleeping for %d seconds", sleep_time)
            await asyncio.sleep(sleep_time)


background_runner = BackgroundRunner()
