import logging

from celery import Celery

# Connections MUST be imported to start up the connections.
from celery_app import (  # noqa: F401 - ensure signal registration
    metrics as _metrics,
)
from celery_app.connections import Session, redis_conn
from celery_app.tasks.analytics.lorenz import compute_lorenz_and_gini
from celery_app.tasks.analytics.skill_offset import compute_skill_offset
from celery_app.tasks.api_tokens import (
    flush_api_usage,
    persist_api_token,
    revoke_api_token,
)
from celery_app.tasks.front_page import pull_data
from celery_app.tasks.leaderboard import (
    fetch_season_results,
    fetch_weapon_leaderboard,
)
from celery_app.tasks.misc import pull_aliases, update_weapon_info
from celery_app.tasks.player_detail import fetch_player_data
from celery_app.tasks.ripple_snapshot import refresh_ripple_snapshots
from shared_lib.constants import REDIS_URI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

celery = Celery("tasks", broker=REDIS_URI, backend=REDIS_URI)

# Register tasks with time limits to prevent runaway executions
# soft_time_limit allows graceful cleanup before hard time_limit kills the task
celery.task(name="tasks.pull_data", time_limit=600, soft_time_limit=540)(pull_data)
celery.task(name="tasks.fetch_player_data", time_limit=120, soft_time_limit=100)(
    fetch_player_data
)
celery.task(name="tasks.update_weapon_info", time_limit=300, soft_time_limit=270)(
    update_weapon_info
)
celery.task(name="tasks.pull_aliases", time_limit=300, soft_time_limit=270)(
    pull_aliases
)
celery.task(name="tasks.update_skill_offset", time_limit=300, soft_time_limit=270)(
    compute_skill_offset
)
celery.task(name="tasks.update_lorenz_and_gini", time_limit=300, soft_time_limit=270)(
    compute_lorenz_and_gini
)
celery.task(name="tasks.fetch_weapon_leaderboard", time_limit=300, soft_time_limit=270)(
    fetch_weapon_leaderboard
)
celery.task(name="tasks.fetch_season_results", time_limit=300, soft_time_limit=270)(
    fetch_season_results
)
celery.task(name="tasks.persist_api_token", time_limit=60, soft_time_limit=50)(
    persist_api_token
)
celery.task(name="tasks.revoke_api_token", time_limit=60, soft_time_limit=50)(
    revoke_api_token
)
celery.task(name="tasks.flush_api_usage", time_limit=120, soft_time_limit=100)(
    flush_api_usage
)
celery.task(name="tasks.refresh_ripple_snapshots", time_limit=900, soft_time_limit=840)(
    refresh_ripple_snapshots
)
