import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base

# Default: local SQLite file for demo/dev. Set DATABASE_URL to a Postgres DSN
# (e.g. postgresql://user:pass@host:5432/agentpay) to run against Postgres —
# the schema uses no SQLite-specific types, so the switch is a config change,
# not a code change.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentpay.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
