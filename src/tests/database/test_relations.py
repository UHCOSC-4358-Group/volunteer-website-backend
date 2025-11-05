from sqlalchemy.orm import Session
from datetime import date, time
import pytest
from src.models import pydanticmodels, dbmodels
from src.dependencies.database import relations
from src.util.error import DatabaseError
from src.tests.database.conftest import Factories


def test_get_event_volunteer(db_session: Session, factories: Factories):
    org = factories.organization()
    event = factories.event(org=org, capacity=5)
    v1 = factories.volunteer()
    v2 = factories.volunteer()
    # sign up v1 and v2
    relations.signup_volunteer_event(db_session, v1.id, event.id)
    relations.signup_volunteer_event(db_session, v2.id, event.id)
    # Check if they're signed up
    assert relations.get_event_volunteer(db_session, v1.id, event.id) is not None
    assert relations.get_event_volunteer(db_session, v2.id, event.id) is not None
    # Delete v1
    relations.remove_volunteer_event(db_session, v1.id, event.id)
    # Check v1 is gone
    assert relations.get_event_volunteer(db_session, v1.id, event.id) is None
    # Check v2 is still there
    assert relations.get_event_volunteer(db_session, v2.id, event.id) is not None


def test_signup_admin_and_checks_relationships(
    db_session: Session, factories: Factories
):
    org = factories.organization()
    admin = factories.admin()

    # Sign up admin to org
    relations.signup_org_admin(db_session, org.id, admin.id)
    db_session.refresh(org)
    db_session.refresh(admin)

    assert org.admins[0] == admin
    assert admin.organization == org


def test_signup_increments_and_checks_relationships(
    db_session: Session, factories: Factories
):
    org = factories.organization()
    event = factories.event(org=org, capacity=5)
    v1 = factories.volunteer()
    v2 = factories.volunteer()

    relations.signup_volunteer_event(db_session, v1.id, event.id)

    db_session.refresh(event)
    db_session.refresh(v1)
    db_session.refresh(org)
    assert event.assigned == 1
    assert v1.events[0].event == event
    assert org.events[0] == event
    assert event.volunteers[0].volunteer == v1


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


def test_match_volunteers_to_event(db_session: Session, factories: Factories):

    event_date = date(2025, 12, 4)  # Thursday
    event_start_time = time(4, 30, 0)
    event_end_time = time(7, 30, 0)

    org = factories.organization()
    event = factories.event(
        org=org,
        day=event_date,
        start_time=event_start_time,
        end_time=event_end_time,
        location="Houston",
    )
    event.needed_skills.append(dbmodels.EventSkill(skill="Cleaning"))
    event.needed_skills.append(dbmodels.EventSkill(skill="Cooking"))
    admin = factories.admin(org_id=org.id)

    # Create our volunteers to be matched against

    # Should match everything, score == 10
    v0 = factories.volunteer(first_name="volunteer0", location="Houston")
    v0.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(5, 30, 0),
            end_time=time(7, 0, 0),
        )
    )
    v0.skills.append(dbmodels.VolunteerSkill(skill="Cleaning"))
    v0.skills.append(dbmodels.VolunteerSkill(skill="Cooking"))

    # Should match both schedule and location, score == 8
    v1 = factories.volunteer(first_name="volunteer1", location="Houston")
    v1.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(5, 30, 0),
            end_time=time(7, 0, 0),
        )
    )
    # Should only match time, score == 4
    v2 = factories.volunteer(first_name="volunteer2", location="x")
    v2.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(4, 0, 0),
            end_time=time(6, 30, 0),
        )
    )
    # Shouldn't match anything, score == 0
    v3 = factories.volunteer(first_name="volunteer3", location="x")
    v3.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(2, 30, 0),
            end_time=time(4, 29, 0),
        )
    )

    db_session.commit()

    results = relations.match_volunteers_to_event(db_session, event.id, admin.id)

    for volunteer, score in results:
        if volunteer.first_name == "volunteer0":
            assert score == 10
        if volunteer.first_name == "volunteer1":
            assert score == 8
        elif volunteer.first_name == "volunteer2":
            assert score == 4
        elif volunteer.first_name == "volunteer3":
            assert score == 0


class Test_Event_Type_Helper:
    __test__ = False

    def __init__(
        self,
        name: str,
        date: date,
        start_time: time,
        end_time: time,
        location: str,
        needed_skills: list[str],
    ) -> None:
        self.name = name
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.needed_skills = needed_skills


def test_match_events_to_volunteer(db_session: Session, factories: Factories):
    events: list[Test_Event_Type_Helper] = [
        # Should match everything
        Test_Event_Type_Helper(
            "Food Bank Help",
            date(2025, 12, 4),  # Thursday
            time(4, 30, 0),
            time(6, 0, 0),
            "Houston",
            ["Cooking", "Cleaning"],
        ),
        # Shouldn't match skills
        Test_Event_Type_Helper(
            "Handicap Assistance for Voting",
            date(2025, 12, 4),
            time(4, 30, 0),
            time(6, 0, 0),
            "Houston",
            [],
        ),
        # Shouldn't match skills and location
        Test_Event_Type_Helper(
            "Community Assistance",
            date(2025, 12, 4),
            time(4, 30, 0),
            time(6, 0, 0),
            "Dallas",
            [],
        ),
        # Shouldn't match anything, period
        Test_Event_Type_Helper(
            "Cookfest",
            date(2025, 12, 4),
            time(17, 30, 0),
            time(20, 0, 0),
            "Dallas",
            [],
        ),
    ]

    org = factories.organization()
    for event_object in events:
        new_event = factories.event(
            org=org,
            name=event_object.name,
            day=event_object.date,
            start_time=event_object.start_time,
            end_time=event_object.end_time,
            location=event_object.location,
        )

        for s in event_object.needed_skills:
            new_event.needed_skills.append(dbmodels.EventSkill(skill=s))

    db_session.commit()

    volunteer = factories.volunteer(location="Houston")
    volunteer.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=dbmodels.DayOfWeek.THURSDAY,
            start_time=time(4, 0, 0),
            end_time=time(8, 0, 0),
        )
    )
    volunteer.skills.append(dbmodels.VolunteerSkill(skill="Cooking"))
    volunteer.skills.append(dbmodels.VolunteerSkill(skill="Cleaning"))

    db_session.commit()

    results = relations.match_events_to_volunteer(db_session, volunteer.id)

    for event, score in results:
        if event.name == "Food Bank Help":
            assert score == 10
        if event.name == "Handicap Assistance for Voting":
            assert score == 8
        if event.name == "Community Assistance":
            assert score == 4
        if event.name == "Cookfest":
            assert score == 0


def test_get_volunteer_history(db_session: Session, factories: Factories):
    events_obj: list[Test_Event_Type_Helper] = [
        # Shouldn't match either
        Test_Event_Type_Helper(
            "Food Bank Help",
            date(2025, 12, 4),  # Thursday
            time(11, 30, 0),
            time(14, 0, 0),
            "Houston",
            [],
        ),
        # Same day, but should match due to time
        Test_Event_Type_Helper(
            "Handicap Assistance for Voting",
            date(2025, 11, 4),
            time(5, 30, 0),
            time(6, 0, 0),
            "Houston",
            [],
        ),
        # November 4th, 4:30 - 6
        Test_Event_Type_Helper(
            "Community Assistance",
            date(2025, 11, 4),
            time(4, 30, 0),
            time(6, 0, 0),
            "Houston",
            [],
        ),
        # November 4th, 17:30 - 20
        Test_Event_Type_Helper(
            "Cookfest",
            date(2025, 11, 4),
            time(17, 30, 0),
            time(20, 0, 0),
            "Houston",
            [],
        ),
    ]

    events = []

    org = factories.organization()
    for event_object in events_obj:
        new_event = factories.event(
            org=org,
            name=event_object.name,
            day=event_object.date,
            start_time=event_object.start_time,
            end_time=event_object.end_time,
            location=event_object.location,
        )

        for s in event_object.needed_skills:
            new_event.needed_skills.append(dbmodels.EventSkill(skill=s))

        events.append(new_event)

    db_session.commit()

    volunteer = factories.volunteer()
    for e in events:
        volunteer.events.append(dbmodels.EventVolunteer(event=e))

    db_session.commit()

    results = relations.get_volunteer_history(db_session, volunteer.id)

    assert len(results) == 3
