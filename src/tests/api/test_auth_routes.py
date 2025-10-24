from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import json
from src.models import dbmodels
from src.routers.auth import LoginData
from src.dependencies.auth import hash_password, decodeJWT
from src.tests.factories.pydantic_factories import (
    org as org_factory,
    volunteer as volunteer_factory,
    admin as admin_factory,
)
from src.tests.database.conftest import Factories  # from tests/database/conftest.py


def test_volunteer_signup(client: TestClient, db_session: Session):
    FIRST_NAME = "VOLUNTEER"
    volunteer_create = volunteer_factory.dict(name=FIRST_NAME)

    resp = client.post(f"/auth/vol/signup", json=volunteer_create)

    assert resp.status_code == 201

    assert (
        db_session.execute(
            select(dbmodels.Volunteer).where(
                dbmodels.Volunteer.first_name == FIRST_NAME
            )
        )
        is not None
    )


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


def test_admin_signup(client: TestClient, db_session: Session):
    FIRST_NAME = "ADMIN"
    admin_create = admin_factory.dict(name=FIRST_NAME)

    resp = client.post(f"/auth/org/signup", json=admin_create)

    assert resp.status_code == 201

    assert (
        db_session.execute(
            select(dbmodels.OrgAdmin).where(dbmodels.OrgAdmin.first_name == FIRST_NAME)
        )
        is not None
    )


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
