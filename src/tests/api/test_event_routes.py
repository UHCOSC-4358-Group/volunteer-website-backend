from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from src.tests.factories.pydantic_factories import event as event_factory
from src.tests.database.conftest import Factories  # from tests/database/conftest.py


def test_get_event_ok(client: TestClient, db_session: Session, factories: Factories):
    org = factories.organization()
    ev = factories.event(org=org)

    resp = client.get(f"/events/{ev.id}")
    # If you return ORM models directly, serialization may fail;
    # status code is the simplest assertion.
    assert resp.status_code == 200


# POST /events/create (admin-only)
def test_create_event_admin_happy_path(
    client: TestClient, db_session: Session, factories: Factories, as_admin
):
    org = factories.organization()
    admin = factories.admin()
    # Associate admin to org
    admin.organization = org
    db_session.commit()

    as_admin(admin.id)

    payload = event_factory.dict(org_id=org.id, needed_skills=["Cooking", "Cleaning"])
    resp = client.post("/events/create", json=payload)
    assert resp.status_code == 201


# POST /events/{id}/signup (volunteer-only)
def test_signup_event_as_volunteer(
    client: TestClient, db_session: Session, factories: Factories, as_volunteer
):
    org = factories.organization()
    ev = factories.event(org=org, capacity=2)
    vol = factories.volunteer()

    as_volunteer(vol.id)

    resp = client.post(f"/events/{ev.id}/signup")
    assert resp.status_code == 201

    db_session.refresh(ev)
    assert ev.assigned == 1
