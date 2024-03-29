from celery import Celery
from flask import Flask
from flask_caching import Cache

from flask_app.database import Session  # Not used, necessary for Session setup
from flask_app.routes import create_front_page_bp, create_player_detail_bp

app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})
celery = Celery(
    "tasks", broker="redis://redis:6379", backend="redis://redis:6379"
)

front_page_bp = create_front_page_bp(cache)
app.register_blueprint(front_page_bp)

player_detail_bp = create_player_detail_bp()
app.register_blueprint(player_detail_bp)


def run_dev():
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
