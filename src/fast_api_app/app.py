import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from fast_api_app.background_tasks import background_runner
from fast_api_app.connections import celery, limiter
from fast_api_app.feature_flags import is_comp_leaderboard_enabled
from fast_api_app.middleware import (
    APITokenRateLimitMiddleware,
    APITokenUsageMiddleware,
)
from fast_api_app.pubsub import start_pubsub_listener
from fast_api_app.routes import (
    admin_tokens_router,
    front_page_router,
    infer_router,
    ping_router,
    player_detail_router,
    ripple_docs_router,
    ripple_public_router,
    ripple_router,
    search_router,
    weapon_info_router,
    weapon_leaderboard_router,
)

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    celery.send_task("tasks.pull_data")
    celery.send_task("tasks.update_weapon_info")
    celery.send_task("tasks.pull_aliases")
    celery.send_task("tasks.update_skill_offset")
    celery.send_task("tasks.update_lorenz_and_gini")
    celery.send_task("tasks.fetch_weapon_leaderboard")
    celery.send_task("tasks.fetch_season_results")
    if is_comp_leaderboard_enabled():
        celery.send_task("tasks.refresh_ripple_snapshots")

    start_pubsub_listener()
    asyncio.create_task(background_runner.run())
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(APITokenUsageMiddleware)
app.add_middleware(APITokenRateLimitMiddleware)

# Setup CORS - public API, so allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(front_page_router)
app.include_router(player_detail_router)
app.include_router(search_router)
app.include_router(weapon_info_router)
app.include_router(weapon_leaderboard_router)
app.include_router(infer_router)
app.include_router(ping_router)
app.include_router(ripple_docs_router)
app.include_router(ripple_router)
app.include_router(ripple_public_router)
app.include_router(admin_tokens_router)


# Base route that lists all available routes
@app.get("/api", response_class=HTMLResponse)
async def list_routes():
    html = "<h1>API Endpoints</h1><ul>"
    exclude_paths = [
        "/api/player/",
        "/ws/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/search/",
    ]
    exclude_exact = ["/api"]
    for route in app.routes:
        if (
            hasattr(route, "path")
            and not any(
                route.path.startswith(exclude) for exclude in exclude_paths
            )
            and route.path not in exclude_exact
        ):
            html += f'<li><a href="{route.path}">{route.path}</a></li>'
    html += "</ul>"
    return HTMLResponse(content=html)


# Run the app using Uvicorn programmatically
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
