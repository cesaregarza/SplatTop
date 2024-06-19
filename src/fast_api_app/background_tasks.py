import asyncio
import logging

from fast_api_app.sqlite_tables import (
    AliasManager,
    SeasonResultsManager,
    TableManager,
    WeaponLeaderboardManager,
)
from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)

logger = logging.getLogger(__name__)


class BackgroundRunner:
    def __init__(self, table_managers: list[TableManager]):
        self.table_managers = table_managers
        for manager in self.table_managers:
            manager.initialize_table()

    async def update_table(self, manager: TableManager):
        logger.info("Updating table %s", manager.table_name)
        sleep_time = manager.cadence
        try:
            manager.update_database()
        except Exception as e:
            logger.error(f"Error updating table {manager.table_name}: {e}")
            sleep_time = manager.retry_cadence

        logger.info(
            "Sleeping %s for %d seconds", manager.table_name, sleep_time
        )
        await asyncio.sleep(sleep_time)

    async def run(self):
        logger.info("Starting background task to update tables")
        while True:
            tasks = [
                self.update_table(manager) for manager in self.table_managers
            ]
            await asyncio.gather(*tasks)


background_runner = BackgroundRunner(
    [
        AliasManager(
            "aliases",
            ALIASES_REDIS_KEY,
            cadence=600,
            retry_cadence=60,
        ),
        WeaponLeaderboardManager(
            "weapon_leaderboard_peak",
            WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
            cadence=600,
            retry_cadence=60,
        ),
        SeasonResultsManager(
            "season_results",
            SEASON_RESULTS_REDIS_KEY,
            cadence=600,
            retry_cadence=60,
        ),
    ]
)
