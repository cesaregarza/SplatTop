import os

import sqlalchemy as db
from dotenv import load_dotenv
from flask import g

load_dotenv()


def create_uri() -> str:
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    dev_mode = os.getenv("DEV_MODE")
    ssl_string = "" if dev_mode is None else "?sslmode=disable"
    return (
        f"postgresql+asyncpg://{user}:{password}@{host}:{port}/"
        f"{db_name}{ssl_string}"
    )


def get_db() -> db.engine.Engine:
    if "db" not in g:
        engine = db.create_engine(create_uri())
        g.db = engine.connect()
        g.db.row_factory = db.Row

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
