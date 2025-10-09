import asyncio
import logging
from time import perf_counter

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
from shared_lib.monitoring import (
    TABLE_REFRESH_DURATION,
    TABLE_REFRESH_SLEEP_SECONDS,
    TABLE_REFRESH_TOTAL,
    metrics_enabled,
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
        outcome = "success"
        start = perf_counter()
        try:
            manager.update_database()
        except Exception as e:
            logger.error(f"Error updating table {manager.table_name}: {e}")
            sleep_time = manager.retry_cadence
            outcome = "error"
        finally:
            duration = perf_counter() - start
            if metrics_enabled():
                TABLE_REFRESH_DURATION.labels(manager.table_name).observe(
                    duration
                )
                TABLE_REFRESH_TOTAL.labels(
                    manager.table_name, outcome
                ).inc()
                TABLE_REFRESH_SLEEP_SECONDS.labels(manager.table_name).set(
                    float(sleep_time)
                )

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
