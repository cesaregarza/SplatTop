import asyncio
import logging
import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flask_app.connections import celery
from flask_app.pubsub import listen_for_updates
from flask_app.routes import temp_player_router
from flask_app.routes.front_page import create_front_page_router

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
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
app.include_router(create_front_page_router())
app.include_router(temp_player_router)


# Background task setup
@app.on_event("startup")
async def startup_event():
    # Send Celery task
    celery.send_task("tasks.pull_data")

    # Start the pubsub listener in a separate daemon thread
    # pubsub_thread = threading.Thread(target=listen_for_updates, daemon=True)
    pubsub_thread = threading.Thread(
        target=asyncio.run, args=(listen_for_updates(),), daemon=True
    )
    pubsub_thread.start()


# Run the app using Uvicorn programmatically
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
