import asyncio
import logging
import os
import threading

from fastapi import BackgroundTasks, FastAPI  # Import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from flask_app.background_tasks import background_runner
from flask_app.connections import celery, redis_conn
from flask_app.pubsub import listen_for_updates
from flask_app.routes import (
    front_page_router,
    player_detail_router,
    search_router,
    weapon_info_router,
)

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
app = FastAPI()

# Setup CORS
if os.getenv("ENV") == "development":
    origins = ["http://localhost:3000"]
else:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(front_page_router)
app.include_router(player_detail_router)
app.include_router(search_router)
app.include_router(weapon_info_router)


# Background task setup
@app.on_event("startup")
async def startup_event():
    # Send Celery task
    celery.send_task("tasks.pull_data")
    celery.send_task("tasks.update_weapon_info")
    celery.send_task("tasks.pull_aliases")

    # Start the pubsub listener in a separate daemon thread
    pubsub_thread = threading.Thread(
        target=asyncio.run, args=(listen_for_updates(),), daemon=True
    )
    pubsub_thread.start()
    asyncio.create_task(background_runner.run())


# Run the app using Uvicorn programmatically
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
