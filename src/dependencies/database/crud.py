from typing import Iterable
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels, pydanticmodels
from ...util import error


def create_location(
    location_obj: pydanticmodels.Location,
    latlong: tuple[float, float] | None = None,
):
    if latlong is None:
        raise error.ExternalServiceError(
            "DB", "create_location was called without latlong"
        )

    latitude = latlong[0]
    longitude = latlong[1]

    time = datetime.now()

    new_location = dbmodels.Location(
        address=location_obj.address,
        city=location_obj.city,
        state=location_obj.state,
        country=location_obj.country,
        zip_code=location_obj.zip_code,
        coordinates=func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        created_at=time,
        updated_at=time,
    )

    return new_location


def update_location(
    old_location: dbmodels.Location,
    new_location: pydanticmodels.Location,
    latlong: tuple[float, float] | None = None,
):

    if latlong is None:
        raise error.ExternalServiceError(
            "DB", "update_location was called without latlong"
        )

    time = datetime.now()

    old_location.address = new_location.address
    old_location.city = new_location.city
    old_location.state = new_location.state
    old_location.country = new_location.country
    old_location.zip_code = new_location.zip_code

    time = datetime.now()
    latitude = latlong[0]
    longitude = latlong[1]
    old_location.coordinates = func.ST_SetSRID(
        func.ST_MakePoint(longitude, latitude), 4326
    )
    old_location.updated_at = time


# Example repo-style usage
def create_volunteer(
    db: Session,
    new_volunteer: pydanticmodels.VolunteerCreate,
    image_url: str | None = None,
    latlong: tuple[float, float] | None = None,
):

    vol = dbmodels.Volunteer(
        email=new_volunteer.email,
        password=new_volunteer.password,
        first_name=new_volunteer.first_name,
        last_name=new_volunteer.last_name,
        description=new_volunteer.description,
        image_url=image_url,
        date_of_birth=new_volunteer.date_of_birth,
    )

    skills: Iterable[str] = getattr(new_volunteer, "skills", None) or []
    for s in {s.strip() for s in skills if s and s.strip()}:
        vol.skills.append(dbmodels.VolunteerSkill(skill=s))

    available_times: Iterable[pydanticmodels.AvailableTime] = (
        getattr(new_volunteer, "available_times", None) or []
    )
    for slot in available_times:
        vol.times_available.append(
            dbmodels.VolunteerAvailableTime(
                start_time=slot.start, end_time=slot.end, day_of_week=slot.day
            )
        )

    if new_volunteer.location is not None:
        if latlong is None:
            raise error.ExternalServiceError(
                "DB", "create_volunteer called without latlong"
            )
        vol.location = create_location(new_volunteer.location, latlong)

    db.add(vol)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("create_volunteer", str(exc))
    db.refresh(vol)
    del vol.password
    return vol


# CREATE OrgAdmin obj
# Check the obj for expected params ^^^
def create_org_admin(
    db: Session,
    new_admin: pydanticmodels.AdminCreate,
    image_url: str | None = None,
):

    admin = dbmodels.OrgAdmin(
        email=new_admin.email,
        password=new_admin.password,
        first_name=new_admin.first_name,
        last_name=new_admin.last_name,
        description=new_admin.description,
        image_url=image_url,
        date_of_birth=new_admin.date_of_birth,
    )

    db.add(admin)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("create_org_admin", str(exc))
    db.refresh(admin)
    del admin.password
    return admin


def get_volunteer_login(db: Session, email: str):
    query = select(dbmodels.Volunteer).where(dbmodels.Volunteer.email == email)

    volunteer_login: dbmodels.Volunteer | None = db.execute(query).scalar_one_or_none()

    return volunteer_login


def get_admin_login(db: Session, email: str):
    query = select(dbmodels.OrgAdmin).where(dbmodels.OrgAdmin.email == email)

    admin_login: dbmodels.OrgAdmin | None = db.execute(query).scalar_one_or_none()

    return admin_login


def get_current_volunteer(db: Session, id: int):

    current_volunteer = db.get(dbmodels.Volunteer, id)

    if current_volunteer is not None:
        del current_volunteer.password

    return current_volunteer


def get_current_admin(db: Session, id: int):

    current_admin = db.get(dbmodels.OrgAdmin, id)

    if current_admin is not None:
        del current_admin.password

    return current_admin


def get_org_from_id(db: Session, id: int):

    org = db.get(dbmodels.Organization, id)

    return org


def create_new_org(
    db: Session,
    org: pydanticmodels.OrgCreate,
    admin_id: int,
    image_url: str | None = None,
    latlong: tuple[float, float] | None = None,
):

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("Admin", admin_id)

    new_org = dbmodels.Organization(
        name=org.name,
        description=org.description,
        image_url=image_url,
    )

    new_org.admins.append(found_admin)
    if org.location is not None:
        new_org.location = create_location(org.location, latlong)

    db.add(new_org)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("create_org", str(exc))
    db.refresh(new_org)
    return new_org


def delete_org(db: Session, org_id: int, admin_id: int):

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("Admin", admin_id)

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        raise error.NotFoundError("Organization", org_id)

    if found_admin.org_id != found_org.id:
        raise error.AuthorizationError("Authenticated admin not apart of org!")

    db.delete(found_org)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("delete_org", str(exc))


def update_org_helper(
    old_org: dbmodels.Organization,
    org_updates: pydanticmodels.OrgUpdate,
    image_url: str | None,
    latlong: tuple[float, float] | None = None,
):
    if org_updates.name is not None:
        old_org.name = org_updates.name
    if org_updates.description is not None:
        old_org.description = org_updates.description
    if org_updates.location is not None:
        update_location(old_org.location, org_updates.location, latlong)
    if image_url is not None:
        old_org.image_url = image_url

    return old_org


def update_org(
    db: Session,
    org_id: int,
    org_updates: pydanticmodels.OrgUpdate,
    admin_id: int,
    image_url: str | None,
    latlong: tuple[float, float] | None = None,
):
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("Admin", admin_id)

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        raise error.NotFoundError("organization", org_id)

    if found_admin.org_id != found_org.id:
        raise error.AuthorizationError("Admin is not apart of organization!")

    updated_org: dbmodels.Organization = update_org_helper(
        found_org, org_updates, image_url, latlong
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("update_org", str(exc))
    db.refresh(updated_org)
    return updated_org


def get_event_from_id(db: Session, id: int):

    event = db.get(dbmodels.Event, id)

    return event


def create_org_event(
    db: Session,
    event: pydanticmodels.EventCreate,
    admin_id: int,
    image_url: str | None = None,
    latlong: tuple[float, float] | None = None,
):

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("Admin", admin_id)

    if found_admin.org_id != event.org_id:
        raise error.AuthorizationError("Admin is not apart of organization!")

    urgency = pydanticmodels.EventUrgency(
        getattr(event.urgency, "value", event.urgency)
    )

    new_event = dbmodels.Event(
        name=event.name,
        description=event.description,
        image_url=image_url,
        urgency=urgency,
        capacity=event.capacity,
        org_id=event.org_id,
        day=event.day,
        start_time=event.start_time,
        end_time=event.end_time,
    )

    skills: Iterable[str] = getattr(event, "needed_skills", None) or []
    for s in {s.strip() for s in skills if s and s.strip()}:
        new_event.needed_skills.append(dbmodels.EventSkill(skill=s))

    if event.location is not None:
        new_event.location = create_location(event.location, latlong)

    organization = db.get(dbmodels.Organization, new_event.org_id)

    if organization is None:
        raise error.NotFoundError("organization", new_event.org_id)

    organization.events.append(new_event)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("create_org_event", str(exc))
    db.refresh(new_event)
    return new_event


def update_event_helper(
    old_event: dbmodels.Event,
    event_updates: pydanticmodels.EventUpdate,
    image_url: str | None,
    latlong: tuple[float, float] | None = None,
):
    if event_updates.name is not None:
        old_event.name = event_updates.name

    if event_updates.description is not None:
        old_event.description = event_updates.description

    # Gotta update this as well
    if event_updates.location is not None:
        update_location(old_event.location, event_updates.location, latlong)

    if event_updates.needed_skills is not None:
        skills = {
            s.strip()
            for s in event_updates.needed_skills
            if s and isinstance(s, str) and s.strip()
        }
        old_event.needed_skills = [dbmodels.EventSkill(skill=s) for s in sorted(skills)]
    # Accepts both Enum and string values
    if event_updates.urgency is not None:
        u = getattr(event_updates.urgency, "value", event_updates.urgency)

        old_event.urgency = pydanticmodels.EventUrgency(u)

    if image_url is not None:
        old_event.image_url = image_url

    if event_updates.capacity is not None:
        if event_updates.capacity < old_event.assigned:
            raise ValueError(
                "Capacity cannot be less than currently assigned volunteers"
            )
        if event_updates.capacity < 0:
            raise ValueError("Capacity cannot be negative!")
        old_event.capacity = event_updates.capacity

    return old_event


def update_org_event(
    db: Session,
    event_id: int,
    event_updates: pydanticmodels.EventUpdate,
    admin_id: int,
    image_url: str | None,
    latlong: tuple[float, float] | None = None,
):
    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise error.NotFoundError("event", event_id)

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("Admin", admin_id)

    if found_admin.org_id != found_event.org_id:
        raise error.AuthorizationError("Admin is not apart of organization!")

    try:
        new_event = update_event_helper(found_event, event_updates, image_url, latlong)
    except ValueError as exc:
        raise error.ValidationError("Invalid event data", fields={"capacity": str(exc)})

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("update_org_event", str(exc))
    db.refresh(new_event)
    return new_event


def delete_org_event(db: Session, event_id: int, admin_id: int):

    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise error.NotFoundError("event", event_id)

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise error.NotFoundError("Admin", admin_id)

    if found_event.org_id != found_admin.org_id:
        raise error.AuthorizationError("Admin is not apart of organization!")

    db.delete(found_event)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise error.DatabaseOperationError("delete_org_event", str(exc))
