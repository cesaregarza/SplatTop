import os

import sqlalchemy as db
from dotenv import load_dotenv
from flask import current_app, g

load_dotenv()


def create_uri() -> str:
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


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
