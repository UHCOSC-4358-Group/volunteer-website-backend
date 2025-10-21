# Where we handle DB session / CRUD methods
from fastapi import FastAPI, Request
from ...models.dbmodels import Base
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os


# Just simple setup stuff here, we want to make it so our db connection isn't a singleton
# Instead we make an engine our singleton, which can create a session per request
# Better for concurrency and wtv

# As for our chosen postgreSQL db, i recommend Supabase's free tier, sounds like a good deal
# If you need schema examples, here's a link


def build_sessionmaker(db_url: str):
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):

    USER = os.getenv("SUPABASE_USER")
    PASSWORD = os.getenv("SUPABASE_PASSWORD")
    HOST = os.getenv("SUPABASE_HOST")
    PORT = os.getenv("SUPABASE_PORT")
    DB_NAME = os.getenv("SUPABASE_DB_NAME")

    if None in [USER, PASSWORD, HOST, PORT, DB_NAME]:
        raise RuntimeError("SQL URL not set")

    DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}?sslmode=require"

    engine, SessionLocal = build_sessionmaker(DATABASE_URL)

    Base.metadata.create_all(engine)

    app.state.engine = engine
    app.state.SessionLocal = SessionLocal
    try:
        yield
    finally:
        engine.dispose()


# Dependency: per-request Session, no globals
def get_db(request: Request):
    SessionLocal = request.app.state.SessionLocal
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
