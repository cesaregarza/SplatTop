from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from shared_lib.db import create_uri

engine = create_engine(create_uri(), echo=True)
Session = scoped_session(sessionmaker(bind=engine))
