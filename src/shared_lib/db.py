import os

from dotenv import load_dotenv

load_dotenv()


def _build_uri(db_name: str) -> str:
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    dev_mode = os.getenv("DEV_MODE")
    ssl_string = "" if dev_mode is None else "?sslmode=disable"
    return (
        f"postgresql+asyncpg://{user}:{password}@{host}:{port}/"
        f"{db_name}{ssl_string}"
    )


def create_uri() -> str:
    """Primary application DB URI (uses env DB_NAME)."""
    db_name = os.getenv("DB_NAME")
    return _build_uri(db_name)


def create_ranking_uri() -> str:
    """Rankings DB URI (uses env RANKINGS_DB_NAME or falls back to DB_NAME)."""
    db_name = os.getenv("RANKINGS_DB_NAME") or "rankings_db"
    return _build_uri(db_name)
