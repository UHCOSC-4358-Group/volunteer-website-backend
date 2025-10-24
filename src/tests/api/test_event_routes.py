from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import json
from src.models import pydanticmodels, dbmodels
from src.tests.factories.pydantic_factories import event as event_factory
from src.tests.database.conftest import Factories  # from tests/database/conftest.py
from src.dependencies.database import relations


def test_get_event(client: TestClient, db_session: Session, factories: Factories):
    NAME = "EVENT"
    org = factories.organization()
    ev = factories.event(org=org, name=NAME)

    resp = client.get(f"/events/{ev.id}")

    response_body = json.loads(resp.content)

    assert resp.status_code == 200
    assert response_body["name"] == NAME

    # fake event id
    EVENT_FAKE_ID = 29

    resp = client.get(f"/events/{EVENT_FAKE_ID}")

    assert resp.status_code == 404


# POST /events/create (admin-only)
def test_create_event_admin(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):
    NAME = "EVENT"
    org = factories.organization()
    admin = factories.admin()
    # Associate admin to org
    admin.organization = org
    db_session.commit()

    as_admin(admin.id)

    payload = event_factory.dict(
        name=NAME, org_id=org.id, needed_skills=["Cooking", "Cleaning"]
    )
    resp = client.post("/events/create", json=payload)
    response_body = json.loads(resp.content)
    assert resp.status_code == 201
    assert response_body["name"] == NAME

    # Check volunteer checking
    as_volunteer(admin.id)

    resp = client.post("/events/create", json=payload)
    assert resp.status_code == 403


def test_update_event(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):
    UPDATED_NAME = "EVENT"
    org = factories.organization()
    admin = factories.admin()
    admin.organization = org
    event = factories.event(org=org)
    db_session.commit()

    old_description = event.description

    as_admin(admin.id)

    payload = pydanticmodels.EventUpdate(
        name=UPDATED_NAME,
        description=None,
        location=None,
        required_skills=None,
        urgency=None,
        capacity=None,
    ).model_dump()

    resp = client.patch(f"/events/{event.id}", json=payload)
    response_body = json.loads(resp.content)
    assert resp.status_code == 200
    assert response_body["name"] == UPDATED_NAME
    assert response_body["description"] == old_description

    # Check volunteer checking
    as_volunteer(admin.id)

    resp = client.patch(f"/events/{event.id}", json=payload)
    assert resp.status_code == 403


def test_delete_event(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
    as_volunteer,
):

    org = factories.organization()
    admin = factories.admin()
    admin.organization = org
    event = factories.event(org=org)
    db_session.commit()

    as_admin(admin.id)

    event_id = event.id

    resp = client.delete(f"/events/{event_id}")
    assert resp.status_code == 200
    assert db_session.get(dbmodels.Event, event_id) is None

    as_volunteer(admin.id)

    resp = client.delete(f"/events/{event.id}")
    assert resp.status_code == 403


# POST /events/{id}/signup (volunteer-only)
def test_signup_event_as_volunteer(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_volunteer,
    as_admin,
):
    org = factories.organization()
    ev = factories.event(org=org, capacity=2)
    vol = factories.volunteer()

    as_volunteer(vol.id)

    resp = client.post(f"/events/{ev.id}/signup")
    assert resp.status_code == 201

    db_session.refresh(ev)
    assert ev.assigned == 1

    as_admin(vol.id)
    resp = client.post(f"/events/{ev.id}/signup")

    assert resp.status_code == 403


def test_event_volunteer_delete(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_volunteer,
    as_admin,
):
    org = factories.organization()
    ev = factories.event(org=org, capacity=2)
    vol = factories.volunteer()

    db_session.commit()

    # Using relations to simulate on assigned count logic
    relations.signup_volunteer_event(db_session, vol.id, ev.id)

    as_volunteer(vol.id)

    resp = client.delete(f"/events/{ev.id}/dropout")

    response_body = json.loads(resp.content)
    print(response_body)

    assert resp.status_code == 200

    as_admin(vol.id)
    resp = client.post(f"/events/{ev.id}/signup")

    assert resp.status_code == 403
