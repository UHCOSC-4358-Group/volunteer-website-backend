from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import json
import os
from sqlalchemy import select
from io import BytesIO
from mypy_boto3_s3 import S3Client
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
    aws_s3: S3Client,
    as_admin,
    as_volunteer,
):
    NAME = "ORGANIZATION"
    admin = factories.admin()
    org_create = org_factory.dict(name=NAME)

    json_str = json.dumps(org_create)

    fake_image = BytesIO(b"fake image bytes")
    fake_image.name = "profile.png"

    as_admin(admin.id)

    resp = client.post(
        f"/org/create",
        data={"org_data": json_str},
        files={"image": ("profile.png", fake_image, "image/png")},
    )

    assert resp.status_code == 201

    found_org = db_session.execute(
        select(dbmodels.Organization).where(dbmodels.Organization.name == NAME)
    ).scalar_one_or_none()

    assert found_org is not None
    assert found_org.name == NAME

    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

    assert AWS_BUCKET_NAME is not None
    assert aws_s3.list_objects_v2(Bucket=AWS_BUCKET_NAME).get("KeyCount", 0) == 1

    as_volunteer(admin.id)

    resp = client.post(
        f"/org/create",
        data={"org_data": json_str},
        files={"image": ("profile.png", fake_image, "image/png")},
    )

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
        name=UPDATED_NAME, description=None, location=None
    ).model_dump()

    json_str = json.dumps(org_updates)

    resp = client.patch(f"/org/{org.id}", data={"org_updates_data": json_str})
    response_body = json.loads(resp.content)
    assert resp.status_code == 200
    assert response_body["name"] == UPDATED_NAME

    as_volunteer(admin.id)

    resp = client.patch(f"/org/{org.id}", data={"org_updates_data": json_str})

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


def test_get_admin_profile(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):
    # Test 1: Admin with organization and events
    org = factories.organization()
    admin = factories.admin(org_id=org.id)

    # Create some upcoming events
    event1 = factories.event(org_id=org.id, name="Future Event 1")
    event2 = factories.event(org_id=org.id, name="Future Event 2")

    db_session.commit()

    as_admin(admin.id)

    resp = client.get(f"/org/admin/{admin.id}")

    assert resp.status_code == 200

    response_body = json.loads(resp.content)

    assert response_body["admin"]["id"] == admin.id
    assert response_body["admin"]["email"] == admin.email
    assert response_body["organization"] is not None
    assert response_body["organization"]["id"] == org.id
    assert response_body["organization"]["name"] == org.name
    assert len(response_body["upcoming_events"]) >= 2

    # Test 2: Admin without organization
    admin_no_org = factories.admin()
    db_session.commit()

    as_admin(admin_no_org.id)

    resp = client.get(f"/org/admin/{admin_no_org.id}")

    assert resp.status_code == 200

    response_body = json.loads(resp.content)

    assert response_body["admin"]["id"] == admin_no_org.id
    assert response_body["organization"] is None
    assert response_body["upcoming_events"] == []

    # Test 3: Admin trying to access another admin's profile
    another_admin = factories.admin()
    db_session.commit()

    as_admin(admin.id)

    resp = client.get(f"/org/admin/{another_admin.id}")

    assert resp.status_code == 403

    # Test 4: Volunteer trying to access admin profile
    volunteer = factories.volunteer()
    db_session.commit()

    as_volunteer(volunteer.id)

    resp = client.get(f"/org/admin/{admin.id}")

    assert resp.status_code == 403

    # Test 5: Non-existent admin
    FAKE_ADMIN_ID = -999

    as_admin(admin.id)

    resp = client.get(f"/org/admin/{FAKE_ADMIN_ID}")

    assert resp.status_code == 403  # Fails authorization before checking existence
