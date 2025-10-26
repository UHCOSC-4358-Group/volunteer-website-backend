from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from datetime import time
import pytest
import json
import os
from io import BytesIO
from mypy_boto3_s3 import S3Client
from src.models import dbmodels, pydanticmodels
from src.routers.auth import LoginData
from src.dependencies.auth import hash_password, decodeJWT
from src.tests.factories.pydantic_factories import (
    volunteer as volunteer_factory,
    admin as admin_factory,
)
from src.tests.database.conftest import Factories  # from tests/database/conftest.py


def test_volunteer_signup(client: TestClient, db_session: Session, aws_s3: S3Client):
    FIRST_NAME = "VOLUNTEER"
    volunteer_create = volunteer_factory.dict(first_name=FIRST_NAME)

    # Have to use json string since it's a multipart form
    json_str = json.dumps(volunteer_create)

    fake_image = BytesIO(b"fake image bytes")
    fake_image.name = "profile.png"

    resp = client.post(
        f"/auth/vol/signup",
        data={"vol_str": json_str},
        files={"image": ("profile.png", fake_image, "image/png")},
    )

    assert resp.status_code == 201

    found_volunteer = db_session.execute(
        select(dbmodels.Volunteer).where(dbmodels.Volunteer.first_name == FIRST_NAME)
    ).scalar_one_or_none()

    assert found_volunteer is not None
    assert found_volunteer.first_name == FIRST_NAME

    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

    assert AWS_BUCKET_NAME is not None
    assert aws_s3.list_objects_v2(Bucket=AWS_BUCKET_NAME).get("KeyCount", 0) == 1

    assert (
        db_session.execute(
            select(dbmodels.Volunteer).where(
                dbmodels.Volunteer.first_name == FIRST_NAME
            )
        )
        is not None
    )

    # Overlapping times in validation checks
    times = [
        pydanticmodels.AvailableTime(
            day=pydanticmodels.DayOfWeek.FRIDAY, start=time(17), end=time(21)
        ),
        pydanticmodels.AvailableTime(
            day=pydanticmodels.DayOfWeek.FRIDAY, start=time(18), end=time(20)
        ),
    ]

    # Checking object validation
    with pytest.raises(ValueError):
        volunteer_create = volunteer_factory.dict(available_times=times)


def test_volunteer_login(client: TestClient, factories: Factories):
    EMAIL = "example@example.com"
    PASSWORD = "superduper"

    vol = factories.volunteer(email=EMAIL, password=hash_password(PASSWORD))

    login_data = LoginData(email=EMAIL, password=PASSWORD).model_dump()

    resp = client.post("/auth/vol/login", json=login_data)

    assert resp.status_code == 200

    cookie = resp.cookies.get("access_token")
    assert cookie is not None

    decoded_cookie = decodeJWT(cookie)
    assert decoded_cookie is not None
    assert decoded_cookie["userId"] == vol.id


def test_admin_signup(client: TestClient, db_session: Session, aws_s3: S3Client):
    FIRST_NAME = "ADMIN"
    admin_create = admin_factory.dict(first_name=FIRST_NAME)
    json_str = json.dumps(admin_create)

    fake_image = BytesIO(b"fake image bytes")
    fake_image.name = "profile.png"

    resp = client.post(
        f"/auth/org/signup",
        data={"admin_str": json_str},
        files={"image": ("profile.png", fake_image, "image/png")},
    )

    assert resp.status_code == 201

    found_admin = db_session.execute(
        select(dbmodels.OrgAdmin).where(dbmodels.OrgAdmin.first_name == FIRST_NAME)
    ).scalar_one_or_none()

    assert found_admin is not None
    assert found_admin.first_name == FIRST_NAME

    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

    assert AWS_BUCKET_NAME is not None
    assert aws_s3.list_objects_v2(Bucket=AWS_BUCKET_NAME).get("KeyCount", 0) == 1


def test_admin_login(client: TestClient, factories: Factories):
    EMAIL = "example@example.com"
    PASSWORD = "superduper"

    admin = factories.admin(email=EMAIL, password=hash_password(PASSWORD))

    login_data = LoginData(email=EMAIL, password=PASSWORD).model_dump()

    resp = client.post("/auth/org/login", json=login_data)

    assert resp.status_code == 200

    cookie = resp.cookies.get("access_token")
    assert cookie is not None

    decoded_cookie = decodeJWT(cookie)
    assert decoded_cookie is not None
    assert decoded_cookie["userId"] == admin.id


def test_get_volunteer(
    client: TestClient,
    factories: Factories,
    as_volunteer,
    as_admin,
):
    FIRST_NAME = "VOLUNTEER"
    vol = factories.volunteer(first_name=FIRST_NAME)

    as_volunteer(vol.id)

    resp = client.get("auth/vol")
    assert resp.status_code == 200

    # login as admin

    as_admin(vol.id)

    resp = client.get("/auth/vol")
    assert resp.status_code == 403

    # fake volunteer id
    FAKE_ID = -5

    as_volunteer(FAKE_ID)

    resp = client.get("auth/vol")
    assert resp.status_code == 404


def test_get_admin(
    client: TestClient,
    factories: Factories,
    as_volunteer,
    as_admin,
):
    FIRST_NAME = "ADMIN"
    admin = factories.admin(first_name=FIRST_NAME)

    as_admin(admin.id)

    resp = client.get("auth/admin")
    assert resp.status_code == 200

    # login as volunteer

    as_volunteer(admin.id)

    resp = client.get("/auth/admin")
    assert resp.status_code == 403

    # fake admin id
    FAKE_ID = -5

    as_admin(FAKE_ID)

    resp = client.get("auth/admin")
    assert resp.status_code == 404
