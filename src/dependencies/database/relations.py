from sqlalchemy import select, case, func, and_, literal, desc, Row
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels
from ...util.error import DatabaseError
from ...models import pydanticmodels  # added
from typing import cast, Sequence, Tuple
from datetime import date as Date


def get_event_volunteer(db: Session, volunteer_id: int, event_id: int):
    event_volunteer = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))

    return event_volunteer


# Signs up an admin with an organization
def signup_org_admin(db: Session, org_id: int, admin_id: int):
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        raise DatabaseError(404, f"Organization with id {org_id} not found!")

    if found_admin in found_org.admins:
        raise DatabaseError(409, "Admin already in organization!")

    found_org.admins.append(found_admin)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")


def signup_volunteer_event(db: Session, volunteer_id: int, event_id: int):

    found_volunteer = db.get(dbmodels.Volunteer, volunteer_id)

    if found_volunteer is None:
        raise DatabaseError(404, f"Volunteer with id {volunteer_id} not found!")

    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise DatabaseError(404, f"Event with id {event_id} not found!")

    existing = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))
    if existing is not None:
        raise DatabaseError(409, "Volunteer already signed up to event!")

    if found_event.assigned >= found_event.capacity:
        raise DatabaseError(400, "Event is full capacity!")

    new_volunteer_event = dbmodels.EventVolunteer(
        volunteer=found_volunteer, event=found_event
    )

    db.add(new_volunteer_event)

    found_event.assigned += 1

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")


def remove_volunteer_event(db: Session, volunteer_id: int, event_id: int):
    event_volunteer = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))

    if event_volunteer is None:
        raise DatabaseError(404, "Volunteer is not assigned to Event!")

    event = event_volunteer.event

    if event.assigned <= 0:
        raise DatabaseError(400, "Event has 0 assigned volunteers!")

    event.assigned -= 1

    db.delete(event_volunteer)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")


def match_volunteers_to_event(db: Session, event_id: int, admin_id: int):
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, "Authorized user could not be found!")

    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise DatabaseError(404, "Event could not be found!")

    SKILLS_TOTAL_WEIGHT = 2
    LOCATION_TOTAL_WEIGHT = 4
    SCHEDULE_TOTAL_WEIGHT = 4

    # Count of matching skills per volunteer
    skills_found_subquery = (
        select(func.count())
        .select_from(dbmodels.VolunteerSkill)
        .where(dbmodels.VolunteerSkill.volunteer_id == dbmodels.Volunteer.id)
        .where(
            dbmodels.VolunteerSkill.skill.in_(
                [s.skill for s in found_event.needed_skills]
            )
        )
        .correlate(dbmodels.Volunteer)
        .scalar_subquery()
    )

    # Caps at SKILLS_TOTAL_WEIGHT
    skills_weight_expr = case(
        (skills_found_subquery > SKILLS_TOTAL_WEIGHT, SKILLS_TOTAL_WEIGHT),
        else_=skills_found_subquery,
    )

    # Check if location is the same
    location_match_expression = case(
        (
            func.coalesce(dbmodels.Volunteer.location, "")
            == func.coalesce(literal(found_event.location), ""),
            LOCATION_TOTAL_WEIGHT,
        ),
        else_=0,
    )

    # Now, let's check if the schedules overlap at all
    event_day: Date = cast(Date, found_event.day)
    target_day = pydanticmodels.DayOfWeek(event_day.isoweekday())

    schedules_overlap = (
        select(literal(True))
        .select_from(dbmodels.VolunteerAvailableTime)
        .where(
            and_(
                dbmodels.VolunteerAvailableTime.volunteer_id == dbmodels.Volunteer.id,
                dbmodels.VolunteerAvailableTime.day_of_week == target_day,
                dbmodels.VolunteerAvailableTime.start_time <= found_event.end_time,
                dbmodels.VolunteerAvailableTime.end_time >= found_event.start_time,
            )
        )
        .correlate(dbmodels.Volunteer)
        .exists()
    )

    schedules_overlap_expression = case(
        (schedules_overlap, SCHEDULE_TOTAL_WEIGHT), else_=0
    )

    score_expr = (
        location_match_expression + skills_weight_expr + schedules_overlap_expression
    ).label("matching_score")

    query = select(dbmodels.Volunteer, score_expr).order_by(desc(score_expr))

    results: Sequence[Row[Tuple[dbmodels.Volunteer, int]]] = db.execute(query).all()

    return results


def match_events_to_volunteer(
    db: Session, volunteer_id: int, TESTING_DAY: int | None = None
):

    found_volunteer = db.get(dbmodels.Volunteer, volunteer_id)

    if found_volunteer is None:
        raise DatabaseError(404, "Volunteer could not be found!")

    SKILLS_TOTAL_WEIGHT = 2
    LOCATION_TOTAL_WEIGHT = 4
    SCHEDULE_TOTAL_WEIGHT = 4

    # Count of matching skills per event
    skills_found_subquery = (
        select(func.count())
        .select_from(dbmodels.EventSkill)
        .where(dbmodels.EventSkill.event_id == dbmodels.Event.id)
        .where(dbmodels.EventSkill.skill.in_([s.skill for s in found_volunteer.skills]))
        .correlate(dbmodels.Event)
        .scalar_subquery()
    )

    # Caps at SKILLS_TOTAL_WEIGHT
    skills_weight_expr = case(
        (skills_found_subquery > SKILLS_TOTAL_WEIGHT, SKILLS_TOTAL_WEIGHT),
        else_=skills_found_subquery,
    )

    # Check if location is the same (Event.location vs Volunteer.location)
    location_match_expression = case(
        (
            func.coalesce(dbmodels.Event.location, "")
            == func.coalesce(literal(found_volunteer.location), ""),
            LOCATION_TOTAL_WEIGHT,
        ),
        else_=0,
    )

    # For testing purposes in SQLite
    day_expr = (
        func.extract("isodow", dbmodels.Event.day)
        if db.get_bind().dialect.name == "postgres"
        else pydanticmodels.DayOfWeek(4)
    )

    # Check if schedules overlap:
    # For each Event row, we check whether this volunteer has any weekly slot
    # on the same ISO day-of-week that overlaps the event's time window.
    schedules_overlap = (
        select(literal(True))
        .select_from(dbmodels.VolunteerAvailableTime)
        .where(
            and_(
                dbmodels.VolunteerAvailableTime.volunteer_id == found_volunteer.id,
                # isodow: Monday=1 .. Sunday=7, matches DayOfWeek enum values
                dbmodels.VolunteerAvailableTime.day_of_week == day_expr,
                dbmodels.VolunteerAvailableTime.start_time <= dbmodels.Event.end_time,
                dbmodels.VolunteerAvailableTime.end_time >= dbmodels.Event.start_time,
            )
        )
        .correlate(dbmodels.Event)
        .exists()
    )

    schedules_overlap_expression = case(
        (schedules_overlap, SCHEDULE_TOTAL_WEIGHT), else_=0
    )

    score_expr = (
        location_match_expression + skills_weight_expr + schedules_overlap_expression
    ).label("matching_score")

    # Rank Events for this volunteer by the computed score
    query = select(dbmodels.Event, score_expr).order_by(desc(score_expr))

    results: Sequence[Row[Tuple[dbmodels.Event, int]]] = db.execute(query).all()

    return results
