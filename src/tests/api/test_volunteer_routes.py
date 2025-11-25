import pytest
from fastapi.testclient import TestClient
from datetime import date, time, timedelta
from sqlalchemy.orm import Session
import json
from src.models import dbmodels, pydanticmodels
from src.tests.database.conftest import Factories


def test_volunteer_information_success(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_volunteer,
):
    """Test getting volunteer information successfully"""
    # Create volunteer with skills and availability
    volunteer = factories.volunteer()

    skill = dbmodels.VolunteerSkill(volunteer_id=volunteer.id, skill="First Aid")
    availability = dbmodels.VolunteerAvailableTime(
        volunteer_id=volunteer.id,
        day_of_week=pydanticmodels.DayOfWeek(1),
        start_time=time(14, 0, 0),
        end_time=time(17, 0, 0),
    )
    db_session.add_all([skill, availability])

    # Create organization for events
    org = factories.organization()

    # Create upcoming event
    upcoming_event = factories.event(
        org=org,
        name="Future Event",
        day=date.today() + timedelta(days=7),
    )

    # Create assignment for upcoming event
    upcoming_assignment = dbmodels.EventVolunteer(
        event_id=upcoming_event.id,
        volunteer_id=volunteer.id,
    )
    db_session.add(upcoming_assignment)

    # Create past event
    past_event = factories.event(
        org=org,
        name="Past Event",
        day=date.today() - timedelta(days=7),
    )

    # Create assignment for past event
    past_assignment = dbmodels.EventVolunteer(
        event_id=past_event.id,
        volunteer_id=volunteer.id,
    )
    db_session.add(past_assignment)
    db_session.commit()

    as_volunteer(volunteer.id)

    # Make request
    resp = client.get(f"/vol/{volunteer.id}")

    assert resp.status_code == 200

    response_body = json.loads(resp.content)

    # Verify structure
    assert "volunteer" in response_body
    assert "upcoming_events" in response_body
    assert "past_events" in response_body

    # Verify volunteer data
    volunteer_data = response_body["volunteer"]
    assert volunteer_data["id"] == volunteer.id
    assert volunteer_data["email"] == volunteer.email
    assert volunteer_data["first_name"] == volunteer.first_name
    assert "First Aid" in volunteer_data["skills"]

    # Verify upcoming events
    assert len(response_body["upcoming_events"]) == 1
    assert response_body["upcoming_events"][0]["name"] == "Future Event"

    # Verify past events
    assert len(response_body["past_events"]) >= 1
    past_event_names = [e["name"] for e in response_body["past_events"]]
    assert "Past Event" in past_event_names


def test_volunteer_information_unauthorized(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_volunteer,
):
    """Test that volunteer cannot view another volunteer's information"""
    volunteer = factories.volunteer()
    other_volunteer = factories.volunteer()

    db_session.commit()

    as_volunteer(volunteer.id)

    # Try to access other volunteer's info
    resp = client.get(f"/vol/{other_volunteer.id}")

    assert resp.status_code == 403


def test_volunteer_information_admin_can_view_any(
    client: TestClient,
    db_session: Session,
    factories: Factories,
    as_admin,
):
    """Test that admin can view any volunteer's information"""
    volunteer = factories.volunteer()
    admin = factories.admin()

    db_session.commit()

    as_admin(admin.id)

    resp = client.get(f"/vol/{volunteer.id}")

    assert resp.status_code == 200

    response_body = json.loads(resp.content)
    assert response_body["volunteer"]["id"] == volunteer.id


def test_volunteer_information_not_found(
    client: TestClient,
    factories: Factories,
    as_admin,
):
    """Test getting information for non-existent volunteer"""
    FAKE_VOLUNTEER_ID = 1000000
    admin = factories.admin()

    as_admin(admin.id)

    resp = client.get(f"/vol/{FAKE_VOLUNTEER_ID}")

    assert resp.status_code == 404

    response_body = json.loads(resp.content)
    assert "not found" in response_body["detail"].lower()
