from sqlalchemy import (
    select,
    case,
    func,
    and_,
    literal,
    desc,
    Row,
    or_,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels
from ...util import error
from ...models import pydanticmodels
from .scoring import (
    skills_match_score,
    schedule_overlap_score,
    distance_based_location_score,
)
from typing import cast, Sequence, Tuple, Literal, List, Dict, Any
from datetime import date as Date, datetime, time as Time


def get_event_volunteer(db: Session, volunteer_id: int, event_id: int):
    event_volunteer = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))

    return event_volunteer


# Signs up an admin with an organization
def signup_org_admin(db: Session, org_id: int, admin_id: int):
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("admin", admin_id)

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        raise error.NotFoundError("organization", org_id)

    if found_admin in found_org.admins:
        raise error.ConflictError("Admin already in organization")

    found_org.admins.append(found_admin)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("signup_org_admin", str(exc))


def signup_volunteer_event(db: Session, volunteer_id: int, event_id: int):

    found_volunteer = db.get(dbmodels.Volunteer, volunteer_id)

    if found_volunteer is None:
        raise error.NotFoundError("volunteer", volunteer_id)

    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise error.NotFoundError("event", event_id)

    existing = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))
    if existing is not None:
        raise error.ConflictError("Volunteer already signed up to event")

    if found_event.assigned >= found_event.capacity:
        raise error.ValidationError(
            "Invalid join request", {"capacity": "Event is at full capacity!"}
        )

    new_volunteer_event = dbmodels.EventVolunteer(
        volunteer=found_volunteer, event=found_event
    )

    db.add(new_volunteer_event)

    found_event.assigned += 1

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("signup_volunteer_event", str(exc))


def remove_volunteer_event(db: Session, volunteer_id: int, event_id: int):
    event_volunteer = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))

    if event_volunteer is None:
        raise error.NotFoundError(
            "event_volunteer", f"Volunteer id: ${volunteer_id}, Event id: ${event_id}"
        )

    event = event_volunteer.event

    # This is more of a server side error, but we'll see how it plays out client-side
    if event.assigned <= 0:
        raise error.ValidationError("Event already has 0 volunteers!")

    event.assigned -= 1

    db.delete(event_volunteer)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("remove_volunteer_event", str(exc))


def match_volunteers_to_event(
    db: Session,
    event_id: int,
    admin_id: int,
    max_distance: float = 25.0,
    distance_unit: Literal["km", "mile"] = "mile",
):
    """
    SQL-optimized version using SQLAlchemy expressions.
    Better performance for large volunteer pools.
    """
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)
    if found_admin is None:
        raise error.NotFoundError("admin", admin_id)

    found_event = db.get(dbmodels.Event, event_id)
    if found_event is None:
        raise error.NotFoundError("event", event_id)

    SKILLS_MAX = 2
    LOCATION_MAX = 4
    SCHEDULE_MAX = 4

    # Build distance expression (PostGIS)
    center_point = found_event.location.coordinates

    distance_expr = func.ST_Distance(center_point, dbmodels.Location.coordinates)

    # Convert to miles if needed
    if distance_unit == "mile":
        distance_expr = distance_expr * 0.000621371
    else:
        distance_expr = distance_expr / 1000

    # Filter by radius
    within_radius = func.ST_DWithin(
        center_point,
        dbmodels.Location.coordinates,
        max_distance * (1609.34 if distance_unit == "mile" else 1000),
    )

    skills_score = skills_match_score(
        dbmodels.Volunteer.id,
        dbmodels.VolunteerSkill,
        dbmodels.VolunteerSkill.volunteer_id,
        [s.skill for s in found_event.needed_skills],
        max_weight=SKILLS_MAX,
    )

    schedule_score = schedule_overlap_score(
        dbmodels.Volunteer.id,
        found_event.day,
        found_event.start_time,
        found_event.end_time,
        max_weight=SCHEDULE_MAX,
    )

    location_score = distance_based_location_score(
        distance_expr, max_distance, max_weight=LOCATION_MAX
    )

    total_score = (location_score + skills_score + schedule_score).label("total_score")

    # Build query
    query = (
        select(
            dbmodels.Volunteer,
            total_score,
        )
        .join(dbmodels.Location, dbmodels.Volunteer.location_id == dbmodels.Location.id)
        .where(within_radius)
        .order_by(desc(total_score))
    )

    results = db.execute(query).all()

    return results


def match_events_to_volunteer(
    db: Session,
    volunteer_id: int,
    max_distance: float = 25.0,
    distance_unit: Literal["km", "mile"] = "mile",
):
    """
    Find and rank events that match a volunteer's profile.
    Uses same scoring system as match_volunteers_to_event for consistency.
    """
    found_volunteer = db.get(dbmodels.Volunteer, volunteer_id)

    if found_volunteer is None:
        raise error.NotFoundError("volunteer", volunteer_id)

    if found_volunteer.location is None:
        raise error.ValidationError(
            "Volunteer must have a location set to match events"
        )

    SKILLS_MAX = 2
    LOCATION_MAX = 4
    SCHEDULE_MAX = 4

    # Build distance expression (PostGIS)
    volunteer_point = found_volunteer.location.coordinates

    distance_expr = func.ST_Distance(volunteer_point, dbmodels.Location.coordinates)

    # Convert to miles if needed
    if distance_unit == "mile":
        distance_expr = distance_expr * 0.000621371
    else:
        distance_expr = distance_expr / 1000

    # Filter by radius
    within_radius = func.ST_DWithin(
        volunteer_point,
        dbmodels.Location.coordinates,
        max_distance * (1609.34 if distance_unit == "mile" else 1000),
    )

    # Reuse scoring components
    skills_score = skills_match_score(
        dbmodels.Event.id,
        dbmodels.EventSkill,
        dbmodels.EventSkill.event_id,
        [s.skill for s in found_volunteer.skills],
        max_weight=SKILLS_MAX,
    )

    # For schedule overlap, we need to check if the volunteer's availability
    # overlaps with the event's day/time
    day_expr = func.extract("isodow", dbmodels.Event.day)
    day_of_week_type = dbmodels.VolunteerAvailableTime.day_of_week.type
    day_expr_casted = func.cast(day_expr, day_of_week_type)

    schedules_overlap = (
        select(literal(True))
        .select_from(dbmodels.VolunteerAvailableTime)
        .where(
            and_(
                dbmodels.VolunteerAvailableTime.volunteer_id == found_volunteer.id,
                dbmodels.VolunteerAvailableTime.day_of_week == day_expr_casted,
                dbmodels.VolunteerAvailableTime.start_time <= dbmodels.Event.end_time,
                dbmodels.VolunteerAvailableTime.end_time >= dbmodels.Event.start_time,
            )
        )
        .correlate(dbmodels.Event)
        .exists()
    )

    schedule_score = case((schedules_overlap, SCHEDULE_MAX), else_=0)

    location_score = distance_based_location_score(
        distance_expr, max_distance, max_weight=LOCATION_MAX
    )

    total_score = (location_score + skills_score + schedule_score).label(
        "matching_score"
    )

    # Build query
    query = (
        select(dbmodels.Event, total_score)
        .join(dbmodels.Location, dbmodels.Event.location_id == dbmodels.Location.id)
        .where(within_radius)
        .order_by(desc(total_score))
    )

    results: Sequence[Row[Tuple[dbmodels.Event, int]]] = db.execute(query).all()

    return results


def get_volunteer_history(db: Session, volunteer_id: int) -> List[Dict[str, Any]]:
    """
    Get all past events that a volunteer participated in, as plain dictionaries.
    Uses PostgreSQL's CURRENT_DATE and CURRENT_TIME for server-side filtering.
    Returns events ordered by most recent first.
    """
    past_event_predicate = or_(
        dbmodels.Event.day < func.current_date(),
        and_(
            dbmodels.Event.day == func.current_date(),
            dbmodels.Event.end_time < func.current_time(),
        ),
    )

    query = (
        select(dbmodels.Event)
        .join(
            dbmodels.EventVolunteer,
            dbmodels.Event.id == dbmodels.EventVolunteer.event_id,
        )
        .join(
            dbmodels.Volunteer,
            dbmodels.Volunteer.id == dbmodels.EventVolunteer.volunteer_id,
        )
        .where(dbmodels.Volunteer.id == volunteer_id)
        .where(past_event_predicate)
        .order_by(desc(dbmodels.Event.day), desc(dbmodels.Event.end_time))
    )

    # returns Row objects with a single Event; get the scalar Event instances
    events = db.execute(query).scalars().all()

    past_events: List[Dict[str, Any]] = []
    for event in events:
        location: Dict[str, Any] = {}
        if event.location is not None:
            location = {
                "address": event.location.address,
                "city": event.location.city,
                "state": event.location.state,
                "country": event.location.country,
                "zip_code": event.location.zip_code,
            }

        past_events.append(
            {
                "event_id": event.id,
                "name": event.name,
                "location": location,
                "day": str(event.day) if event.day else None,
                "start_time": (str(event.start_time) if event.start_time else None),
                "end_time": str(event.end_time) if event.end_time else None,
                "urgency": str(event.urgency) if event.urgency is not None else None,
            }
        )

    return past_events


def get_org_past_volunteers(db: Session, org_id: int) -> List[Dict[str, Any]]:
    """
    Return all volunteers who participated in past events for the given organization.
    Each volunteer dict includes volunteer info and a list of past events they worked,
    with computed hours for each event when start/end times are present.
    """
    # predicate for past events (same logic as get_volunteer_history)
    past_event_predicate = or_(
        dbmodels.Event.day < func.current_date(),
        and_(
            dbmodels.Event.day == func.current_date(),
            dbmodels.Event.end_time < func.current_time(),
        ),
    )

    # find distinct volunteers who have EventVolunteer rows for past events of the org
    query = (
        select(dbmodels.Volunteer)
        .join(
            dbmodels.EventVolunteer,
            dbmodels.Volunteer.id == dbmodels.EventVolunteer.volunteer_id,
        )
        .join(dbmodels.Event, dbmodels.Event.id == dbmodels.EventVolunteer.event_id)
        .where(dbmodels.Event.org_id == org_id)
        .where(past_event_predicate)
        .distinct()
    )

    volunteers = db.execute(query).scalars().all()

    results: List[Dict[str, Any]] = []

    for vol in volunteers:
        # fetch the volunteer's past assignments for this org
        assignments = (
            db.query(dbmodels.EventVolunteer, dbmodels.Event)
            .join(dbmodels.Event, dbmodels.EventVolunteer.event_id == dbmodels.Event.id)
            .filter(
                dbmodels.EventVolunteer.volunteer_id == vol.id,
                dbmodels.Event.org_id == org_id,
                past_event_predicate,
            )
            .order_by(dbmodels.Event.day.desc(), dbmodels.Event.end_time.desc())
            .all()
        )

        event_list: List[Dict[str, Any]] = []
        for ev_assignment, ev in assignments:
            # compute hours if start_time and end_time present
            hours: float | None = None
            if (
                ev.start_time is not None
                and ev.end_time is not None
                and ev.day is not None
            ):
                try:
                    # combine with the event day to get datetimes for subtraction
                    start_dt = datetime.combine(ev.day, ev.start_time)
                    end_dt = datetime.combine(ev.day, ev.end_time)
                    delta = end_dt - start_dt
                    hours = round(delta.total_seconds() / 3600.0, 2)
                except Exception:
                    hours = None

            location: Dict[str, Any] = {}
            if ev.location is not None:
                location = {
                    "address": ev.location.address,
                    "city": ev.location.city,
                    "state": ev.location.state,
                    "country": ev.location.country,
                    "zip_code": ev.location.zip_code,
                }

            event_list.append(
                {
                    "event_id": ev.id,
                    "description": ev.description,
                    "skills": [skill.skill for skill in (ev.needed_skills or [])],
                    "name": ev.name,
                    "day": str(ev.day) if ev.day else None,
                    "start_time": (str(ev.start_time) if ev.start_time else None),
                    "end_time": (str(ev.end_time) if ev.end_time else None),
                    "hours": hours,
                    "location": location,
                }
            )

        results.append(
            {
                "volunteer": {
                    "id": vol.id,
                    "first_name": vol.first_name,
                    "last_name": vol.last_name,
                    "email": vol.email,
                },
                "past_events": event_list,
            }
        )

    return results
