from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import json
from src.models import pydanticmodels, dbmodels
from src.tests.factories.pydantic_factories import (
    org as org_factory,
)
from src.tests.database.conftest import Factories  # from tests/database/conftest.py


def test_get_org_details(client: TestClient, db_session: Session, factories: Factories):
    NAME = "ORG"
    org = factories.organization()

    db_session.commit()

    resp = client.get(f"/org/{org.id}")

    assert resp.status_code == 200

    FAKE_ORG_ID = -5

    resp = client.get(f"/org/{FAKE_ORG_ID}")

    assert resp.status_code == 404


def test_create_org(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):
    NAME = "ORGANIZATION"
    admin = factories.admin()
    org_create = org_factory.dict(name=NAME)

    as_admin(admin.id)

    resp = client.post(f"/org/create", json=org_create)

    assert resp.status_code == 201

    as_volunteer(admin.id)

    resp = client.post(f"/org/create", json=org_create)

    assert resp.status_code == 403


def test_update_org_from_id(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):
    UPDATED_NAME = "ORGANIZATION"
    org = factories.organization()
    admin = factories.admin(org_id=org.id)

    as_admin(admin.id)

    org_updates = pydanticmodels.OrgUpdate(
        name=UPDATED_NAME, description=None, location=None, image_url=None
    ).model_dump()

    resp = client.patch(f"/org/{org.id}", json=org_updates)
    response_body = json.loads(resp.content)
    assert resp.status_code == 200
    assert response_body["name"] == UPDATED_NAME

    as_volunteer(admin.id)

    resp = client.patch(f"/org/{org.id}", json=org_updates)

    assert resp.status_code == 403


def test_delete_org_from_id(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):
    org = factories.organization()
    admin = factories.admin(org_id=org.id)

    org_id = org.id

    as_admin(admin.id)

    resp = client.delete(f"/org/{org.id}")

    assert resp.status_code == 200

    assert db_session.get(dbmodels.Organization, org_id) is None

    as_volunteer(admin.id)

    resp = client.delete(f"/org/{org.id}")

    assert resp.status_code == 403
