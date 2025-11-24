# Where we handle DB session / CRUD methods
import logging
from fastapi import FastAPI, Request
from ...models.dbmodels import Base
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from ..aws import create_bucket
import os


# Just simple setup stuff here, we want to make it so our db connection isn't a singleton
# Instead we make an engine our singleton, which can create a session per request
# Better for concurrency and wtv

# As for our chosen postgreSQL db, i recommend Supabase's free tier, sounds like a good deal
# If you need schema examples, here's a link


def build_sessionmaker(db_url: str, use_pooler: bool = False):
    if use_pooler:
        engine = create_engine(db_url, poolclass=NullPool, plugins=["geoalchemy2"])
    else:
        engine = create_engine(db_url, pool_pre_ping=True, plugins=["geoalchemy2"])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):

    USER = os.getenv("SUPABASE_USER")
    PASSWORD = os.getenv("SUPABASE_PASSWORD")
    HOST = os.getenv("SUPABASE_HOST")
    PORT = os.getenv("SUPABASE_PORT")
    DB_NAME = os.getenv("SUPABASE_DB_NAME")
    USE_POOLER = os.getenv("USE_SUPABASE_POOLER") == "true"

    if None in [USER, PASSWORD, HOST, PORT, DB_NAME]:
        raise RuntimeError("SQL URL not set")

    DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}?sslmode=require"

    engine, SessionLocal = build_sessionmaker(DATABASE_URL, use_pooler=USE_POOLER)

    Base.metadata.create_all(engine)

    s3 = create_bucket()

    app.state.engine = engine
    app.state.SessionLocal = SessionLocal
    app.state.s3 = s3
    try:
        yield
    finally:
        engine.dispose()
        logging.shutdown()


# Dependency: per-request Session, no globals
def get_db(request: Request):
    SessionLocal = request.app.state.SessionLocal
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
