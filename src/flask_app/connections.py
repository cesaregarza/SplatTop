import redis
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from shared_lib.constants import REDIS_HOST, REDIS_PORT
from shared_lib.db import create_uri

engine = create_engine(create_uri())
Session = scoped_session(sessionmaker(bind=engine))

REDIS_URI = f"redis://{REDIS_HOST}:{REDIS_PORT}"
celery = Celery("tasks", broker=REDIS_URI, backend=REDIS_URI)

pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, max_connections=10)
redis_conn = redis.Redis(connection_pool=pool)
