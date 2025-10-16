# Where we handle DB session / CRUD methods
from fastapi import FastAPI, Request
from ..models.models import VolunteerCreate, AdminCreate
from ..models.dbmodels import Base
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
    # settings.database_url should come from env/config
    url = os.getenv("SQLALCHEMY_DATABASE_URL")
    if url is None:
        raise RuntimeError("SQL URL not set")

    engine, SessionLocal = build_sessionmaker(url)

    Base.metadata.create_all(engine)

    app.state.engine = engine
    app.state.SessionLocal = SessionLocal
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)


# Dependency: per-request Session, no globals
def get_db(request: Request):
    SessionLocal = request.app.state.SessionLocal
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Example repo-style usage
def create_volunteer(db: Session, data: VolunteerCreate): ...


# ... perform db operations ...


# CREATE OrgAdmin obj
# Check the obj for expected params ^^^
def create_org_admin(db, volunteer: AdminCreate): ...
