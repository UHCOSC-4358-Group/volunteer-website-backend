from sqlalchemy.orm import Session
from datetime import date, time
import pytest
from src.models import pydanticmodels, dbmodels
from src.dependencies.database.crud import create_location
from src.dependencies.database import relations
from src.tests.database.conftest import Factories
from src.util import error


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
    with pytest.raises(error.ConflictError) as exc:
        relations.signup_volunteer_event(db_session, v1.id, event.id)
    assert exc.value.status_code == 409
    db_session.refresh(event)
    assert event.assigned == 1

    # New volunteer rejected due to capacity; assigned unchanged
    with pytest.raises(error.ValidationError) as exc:
        relations.signup_volunteer_event(db_session, v2.id, event.id)
    assert exc.value.status_code == 422
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
    with pytest.raises(error.NotFoundError) as exc:
        relations.remove_volunteer_event(db_session, v1.id, event.id)
    assert exc.value.status_code == 404
    db_session.refresh(event)
    assert event.assigned == 0


def test_match_volunteers_to_event(db_session: Session, factories: Factories):

    event_date = date(2025, 12, 4)  # Thursday
    event_start_time = time(4, 30, 0)
    event_end_time = time(7, 30, 0)

    org = factories.organization()

    event_location = create_location(
        pydanticmodels.Location(
            address="218 Produce Row",
            city="San Antonio",
            state="TX",
            country="USA",
            zip_code="78207",
        ),
        (29.424891, -98.499741),
    )
    event = factories.event(
        org=org,
        day=event_date,
        start_time=event_start_time,
        end_time=event_end_time,
        location_id=event_location.id,
    )
    event.location = event_location
    event.needed_skills.append(dbmodels.EventSkill(skill="Cleaning"))
    event.needed_skills.append(dbmodels.EventSkill(skill="Cooking"))
    admin = factories.admin(org_id=org.id)

    # Create our volunteers to be matched against

    # Should match everything, score == 10

    vol0_location = create_location(
        pydanticmodels.Location(
            address="107 W Houston St",
            city="San Antonio",
            state="Texas",
            country="USA",
            zip_code="78205",
        ),
        (29.4273377, -98.5019135),
    )

    v0 = factories.volunteer(first_name="volunteer0")
    v0.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(5, 30, 0),
            end_time=time(7, 0, 0),
        )
    )
    v0.location = vol0_location
    v0.skills.append(dbmodels.VolunteerSkill(skill="Cleaning"))
    v0.skills.append(dbmodels.VolunteerSkill(skill="Cooking"))

    vol1_location = create_location(
        pydanticmodels.Location(
            address="501 W Cesar E. Chavez Blvd",
            city="San Antonio",
            state="Texas",
            country="USA",
            zip_code="78207",
        ),
        (29.4253989, -98.5042628),
    )
    v1 = factories.volunteer(first_name="volunteer1")
    v1.location = vol1_location
    v1.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(5, 30, 0),
            end_time=time(7, 0, 0),
        )
    )

    vol2_location = create_location(
        pydanticmodels.Location(
            address="3903 N St Mary's",
            city="San Antonio",
            state="Texas",
            country="USA",
            zip_code="78212",
        ),
        (29.792816, -98.5205579),
    )
    # Should only match time, score == 4
    v2 = factories.volunteer(first_name="volunteer2")
    v2.location = vol2_location
    v2.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(4, 0, 0),
            end_time=time(6, 30, 0),
        )
    )
    # Shouldn't match anything, score == 0
    v3 = factories.volunteer(first_name="volunteer3")
    v3.times_available.append(
        dbmodels.VolunteerAvailableTime(
            day_of_week=pydanticmodels.DayOfWeek.THURSDAY,
            start_time=time(2, 30, 0),
            end_time=time(4, 29, 0),
        )
    )

    db_session.commit()

    results = relations.match_volunteers_to_event(
        db_session, event.id, admin.id, max_distance=10, distance_unit="mile"
    )
    assert len(results) == 2
    assert results[0][0] == v0
    assert results[1][0] == v1


class Test_Event_Type_Helper:
    __test__ = False

    def __init__(
        self,
        name: str,
        date: date,
        start_time: time,
        end_time: time,
        location: dbmodels.Location,
        needed_skills: list[str],
    ) -> None:
        self.name = name
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.needed_skills = needed_skills


generic_pydantic_model = pydanticmodels.Location(
    address=".    ", city=".     ", state=".    ", zip_code=".    ", country=".     "
)


def test_match_events_to_volunteer(db_session: Session, factories: Factories):
    events: list[Test_Event_Type_Helper] = [
        # Should match everything
        Test_Event_Type_Helper(
            "Food Bank Help",
            date(2025, 12, 4),  # Thursday
            time(4, 30, 0),
            time(6, 0, 0),
            # < 2 miles
            create_location(generic_pydantic_model, (29.8, -98.5)),
            ["Cooking", "Cleaning"],
        ),
        # Shouldn't match skills, ok location
        Test_Event_Type_Helper(
            "Handicap Assistance for Voting",
            date(2025, 12, 4),
            time(4, 30, 0),
            time(6, 0, 0),
            # ~ 31 miles
            create_location(generic_pydantic_model, (29.8, -98.0)),
            [],
        ),
        # Shouldn't match skills and poor location
        Test_Event_Type_Helper(
            "Community Assistance",
            date(2025, 12, 4),
            time(4, 30, 0),
            time(6, 0, 0),
            # ~ 47 miles
            create_location(generic_pydantic_model, (30.3, -98.0)),
            [],
        ),
        # Shouldn't match anything, period
        Test_Event_Type_Helper(
            "Cookfest",
            date(2025, 12, 4),
            time(17, 30, 0),
            time(20, 0, 0),
            # 88 miles away
            create_location(generic_pydantic_model, (31.0, -99.0)),
            [],
        ),
    ]

    org = factories.organization()
    db_events = []
    for event_object in events:
        new_event = factories.event(
            org=org,
            name=event_object.name,
            day=event_object.date,
            start_time=event_object.start_time,
            end_time=event_object.end_time,
        )

        new_event.location = event_object.location
        for s in event_object.needed_skills:
            new_event.needed_skills.append(dbmodels.EventSkill(skill=s))
        db_events.append(new_event)

    db_session.commit()

    volunteer = factories.volunteer()

    volunteer.location = create_location(
        generic_pydantic_model, (29.792816, -98.5205579)
    )
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

    results = relations.match_events_to_volunteer(db_session, volunteer.id, 50.0)

    assert len(results) == 3
    assert results[0][0] == db_events[0]
    assert results[1][0] == db_events[1]
    assert results[2][0] == db_events[2]


def test_get_volunteer_history(db_session: Session, factories: Factories):
    events: list[Test_Event_Type_Helper] = [
        # Shouldn't match
        Test_Event_Type_Helper(
            "Food Bank Help",
            date(2050, 12, 4),
            time(4, 30, 0),
            time(6, 0, 0),
            # < 2 miles
            create_location(generic_pydantic_model, (29.8, -98.5)),
            ["Cooking", "Cleaning"],
        ),
        # Shouldn't match
        Test_Event_Type_Helper(
            "Handicap Assistance for Voting",
            date(2050, 12, 3),
            time(4, 30, 0),
            time(6, 0, 0),
            # ~ 31 miles
            create_location(generic_pydantic_model, (29.8, -98.0)),
            [],
        ),
        # Should match
        Test_Event_Type_Helper(
            "Community Assistance",
            date(2022, 12, 5),
            time(4, 30, 0),
            time(6, 0, 0),
            # ~ 47 miles
            create_location(generic_pydantic_model, (30.3, -98.0)),
            [],
        ),
        # Should match
        Test_Event_Type_Helper(
            "Cookfest",
            date(2022, 12, 4),
            time(17, 30, 0),
            time(20, 0, 0),
            # 88 miles away
            create_location(generic_pydantic_model, (31.0, -99.0)),
            [],
        ),
    ]

    new_events: list[dbmodels.Event] = []

    org = factories.organization()
    for event_object in events:
        new_event = factories.event(
            org=org,
            name=event_object.name,
            day=event_object.date,
            start_time=event_object.start_time,
            end_time=event_object.end_time,
        )

        new_event.location = event_object.location
        for s in event_object.needed_skills:
            new_event.needed_skills.append(dbmodels.EventSkill(skill=s))

        new_events.append(new_event)

    db_session.commit()

    volunteer = factories.volunteer()
    for e in new_events:
        volunteer.events.append(dbmodels.EventVolunteer(event=e))

    db_session.commit()

    results = relations.get_volunteer_history(db_session, volunteer.id)

    assert len(results) == 2
    assert results[0][0] == new_events[2]
    assert results[1][0] == new_events[3]
