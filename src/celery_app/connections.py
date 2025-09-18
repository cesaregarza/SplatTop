import redis
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from shared_lib.constants import REDIS_HOST, REDIS_PORT
from shared_lib.db import create_ranking_uri, create_uri

engine = create_engine(create_uri().replace("asyncpg", "psycopg2"))
Session = scoped_session(sessionmaker(bind=engine))
redis_conn = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)

rankings_async_engine = create_async_engine(create_ranking_uri())
rankings_async_session = scoped_session(
    sessionmaker(
        bind=rankings_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
)
