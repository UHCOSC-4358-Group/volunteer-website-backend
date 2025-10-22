from sqlalchemy.orm import Session
from src.dependencies.database import relations
from src.util.error import DatabaseError
from conftest import Factories
import pytest


def test_signup_increments_and_enforces_capacity(
    db_session: Session, factories: Factories
):
    org = factories.organization()
    event = factories.event(org=org, capacity=1)
    v1 = factories.volunteer()
    v2 = factories.volunteer()

    # First signup succeeds
    relations.signup_volunteer_event(db_session, v1.id, event.id)
    db_session.refresh(event)
    assert event.assigned == 1

    # Duplicate signup rejected; assigned unchanged
    with pytest.raises(DatabaseError) as exc:
        relations.signup_volunteer_event(db_session, v1.id, event.id)
    assert exc.value.status_code == 409
    db_session.refresh(event)
    assert event.assigned == 1

    # New volunteer rejected due to capacity; assigned unchanged
    with pytest.raises(DatabaseError) as exc:
        relations.signup_volunteer_event(db_session, v2.id, event.id)
    assert exc.value.status_code == 400
    db_session.refresh(event)
    assert event.assigned == 1


def test_remove_decrements_and_deletes_link(db_session: Session, factories: Factories):
    org = factories.organization()
    event = factories.event(org=org, capacity=2)
    v1 = factories.volunteer()

    # Signs up volunteer 1 successfully
    relations.signup_volunteer_event(db_session, v1.id, event.id)
    db_session.refresh(event)
    assert event.assigned == 1

    # Removes volunteer 1 successfully
    relations.remove_volunteer_event(db_session, v1.id, event.id)
    db_session.refresh(event)
    assert event.assigned == 0

    # Tries to re-remove volunteer 1 and fails with a 404
    with pytest.raises(DatabaseError) as exc:
        relations.remove_volunteer_event(db_session, v1.id, event.id)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Volunteer is not assigned to Event!"
    db_session.refresh(event)
    assert event.assigned == 0
