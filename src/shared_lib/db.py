import os

from dotenv import load_dotenv

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
