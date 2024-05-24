import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from shared_lib.constants import REDIS_HOST, REDIS_PORT
from shared_lib.db import create_uri

engine = create_engine(create_uri().replace("asyncpg", "psycopg2"))
Session = scoped_session(sessionmaker(bind=engine))
redis_conn = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)
