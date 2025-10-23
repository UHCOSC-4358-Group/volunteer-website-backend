import pytest
from contextlib import asynccontextmanager
from typing import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.main import app as fastapi_app
from src.dependencies.database.config import get_db
from src.dependencies.auth import get_current_user, UserTokenInfo


@asynccontextmanager
async def _noop_lifespan(app: FastAPI):
    # Avoid real DB init in tests
    yield


@pytest.fixture
def app(db_session: Session) -> Generator[FastAPI, None, None]:
    app = fastapi_app
    app.router.lifespan_context = _noop_lifespan

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def as_admin(app: FastAPI):
    def _apply(user_id: int):
        app.dependency_overrides[get_current_user] = lambda: UserTokenInfo(
            user_id=user_id, user_type="admin"
        )

    yield _apply
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_volunteer(app: FastAPI):
    def _apply(user_id: int):
        app.dependency_overrides[get_current_user] = lambda: UserTokenInfo(
            user_id=user_id, user_type="volunteer"
        )

    yield _apply
    app.dependency_overrides.pop(get_current_user, None)
