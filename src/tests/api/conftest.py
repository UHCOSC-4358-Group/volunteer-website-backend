import pytest
from contextlib import asynccontextmanager
from typing import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import boto3
from mypy_boto3_s3 import S3Client
from moto import mock_aws
import os
from src.main import app as fastapi_app
from src.dependencies.database.config import get_db
from src.dependencies.aws import get_s3
from src.dependencies.auth import get_current_user, UserTokenInfo
from src.dependencies.aws import create_bucket


@asynccontextmanager
async def _noop_lifespan(app: FastAPI):
    # Avoid real DB init in tests
    yield


@pytest.fixture
def aws_s3() -> Generator[S3Client, None, None]:
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket_name = os.getenv("AWS_BUCKET_NAME", "test-bucket")
        s3.create_bucket(Bucket=bucket_name)
        yield s3


@pytest.fixture
def app(db_session: Session, aws_s3: S3Client) -> Generator[FastAPI, None, None]:
    app = fastapi_app
    app.router.lifespan_context = _noop_lifespan

    def _override_get_db():
        yield db_session

    def _override_aws():
        yield aws_s3

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_s3] = _override_aws

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
