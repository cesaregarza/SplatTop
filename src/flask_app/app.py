import logging
import os
from threading import Thread

from celery import Celery
from flask import Flask
from flask_caching import Cache
from flask_cors import CORS
from flask_socketio import SocketIO

from flask_app.connections import Session, celery, redis_conn
from flask_app.pubsub import listen_for_updates
from flask_app.routes import create_front_page_bp, create_player_detail_bp
from flask_app.routes.temp_player import create_temp_player_bp

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

if os.getenv("ENV") == "development":
    dev_host = "http://localhost:3000"
    CORS(app, resources={r"/*": {"origins": dev_host}})
    socketio = SocketIO(
        app, cors_allowed_origins=dev_host, asyncmode="eventlet"
    )
elif os.getenv("ENV") == "production":
    CORS(app)
    socketio = SocketIO(app, asyncmode="eventlet")


cache = Cache(app, config={"CACHE_TYPE": "simple"})

front_page_bp = create_front_page_bp()
app.register_blueprint(front_page_bp)

player_detail_bp = create_player_detail_bp()
app.register_blueprint(player_detail_bp)

temp_player_bp = create_temp_player_bp(socketio)
app.register_blueprint(temp_player_bp)

thread = Thread(target=listen_for_updates, args=(socketio,), daemon=True)
thread.start()

celery.send_task("tasks.pull_data")


def run_dev():
    from werkzeug.middleware.profiler import ProfilerMiddleware

    app.config["PROFILE"] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run(host="0.0.0.0", port=5000, debug=True)
