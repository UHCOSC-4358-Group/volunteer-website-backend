from typing import Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels, pydanticmodels
from ...util.error import DatabaseError


# For error handling...
# For retrieval, we can off load the error handling to whoever is calling the function
# For other methods, such as creating, deleting, updating, we'll throw a custom DatabaseError


# Example repo-style usage
def create_volunteer(
    db: Session,
    new_volunteer: pydanticmodels.VolunteerCreate,
    image_url: str | None = None,
):

    vol = dbmodels.Volunteer(
        email=new_volunteer.email,
        password=new_volunteer.password,
        first_name=new_volunteer.first_name,
        last_name=new_volunteer.last_name,
        description=new_volunteer.description,
        image_url=image_url,
        location=new_volunteer.location,
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

    db.add(vol)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
    db.refresh(vol)
    return vol


# CREATE OrgAdmin obj
# Check the obj for expected params ^^^
def create_org_admin(
    db: Session, new_admin: pydanticmodels.AdminCreate, image_url: str | None = None
):

    admin = dbmodels.OrgAdmin(
        email=new_admin.email,
        password=new_admin.password,
        first_name=new_admin.first_name,
        last_name=new_admin.last_name,
        description=new_admin.description,
        image_url=image_url,
    )

    db.add(admin)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
    db.refresh(admin)
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

    return current_volunteer


def get_current_admin(db: Session, id: int):

    current_admin = db.get(dbmodels.OrgAdmin, id)

    return current_admin


def get_org_from_id(db: Session, id: int):

    org = db.get(dbmodels.Organization, id)

    return org


def create_new_org(
    db: Session,
    org: pydanticmodels.OrgCreate,
    admin_id: int,
    image_url: str | None = None,
):

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    new_org = dbmodels.Organization(
        name=org.name,
        location=org.location,
        description=org.description,
        image_url=image_url,
    )

    new_org.admins.append(found_admin)

    db.add(new_org)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
    db.refresh(new_org)
    return new_org


def delete_org(db: Session, org_id: int, admin_id: int):

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        raise DatabaseError(404, f"Organization with id {org_id} not found!")

    if found_admin.org_id != found_org.id:
        raise DatabaseError(403, f"Authenticated admin not apart of org!")

    db.delete(found_org)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")


def update_org_helper(
    old_org: dbmodels.Organization, org_updates: pydanticmodels.OrgUpdate
):
    if org_updates.name is not None:
        old_org.name = org_updates.name
    if org_updates.description is not None:
        old_org.description = org_updates.description
    if org_updates.location is not None:
        old_org.location = org_updates.location
    if org_updates.image_url is not None:
        old_org.image_url = org_updates.image_url

    return old_org


def update_org(
    db: Session, org_id: int, org_updates: pydanticmodels.OrgUpdate, admin_id: int
):
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        raise DatabaseError(404, f"Organization with id {org_id} not found!")

    if found_admin.org_id != found_org.id:
        raise DatabaseError(403, "Authenticated admin not apart of org!")

    updated_org: dbmodels.Organization = update_org_helper(found_org, org_updates)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
    db.refresh(updated_org)
    return updated_org


def get_event_from_id(db: Session, id: int):

    event = db.get(dbmodels.Event, id)

    return event


def create_org_event(db: Session, event: pydanticmodels.EventCreate, admin_id: int):

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    if found_admin.org_id != event.org_id:
        raise DatabaseError(403, "Authenticated admin not apart of organization!")

    urgency = pydanticmodels.EventUrgency(
        getattr(event.urgency, "value", event.urgency)
    )

    new_event = dbmodels.Event(
        name=event.name,
        description=event.description,
        location=event.location,
        urgency=urgency,
        capacity=event.capacity,
        org_id=event.org_id,
    )

    skills: Iterable[str] = getattr(event, "needed_skills", None) or []
    for s in {s.strip() for s in skills if s and s.strip()}:
        new_event.needed_skills.append(dbmodels.EventSkill(skill=s))

    organization = db.get(dbmodels.Organization, new_event.org_id)

    if organization is None:
        raise DatabaseError(404, "Organization id tied to event not found!")

    organization.events.append(new_event)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
    db.refresh(new_event)
    return new_event


def update_event_helper(
    old_event: dbmodels.Event, event_updates: pydanticmodels.EventUpdate
):
    if event_updates.name is not None:
        old_event.name = event_updates.name

    if event_updates.description is not None:
        old_event.description = event_updates.description

    if event_updates.location is not None:
        old_event.location = event_updates.location

    if event_updates.required_skills is not None:
        skills = {
            s.strip()
            for s in event_updates.required_skills
            if s and isinstance(s, str) and s.strip()
        }
        old_event.needed_skills = [dbmodels.EventSkill(skill=s) for s in sorted(skills)]
    # Accepts both Enum and string values
    if event_updates.urgency is not None:
        u = getattr(event_updates.urgency, "value", event_updates.urgency)

        old_event.urgency = pydanticmodels.EventUrgency(u)

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
    db: Session, event_id: int, event_updates: pydanticmodels.EventUpdate, admin_id: int
):
    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise DatabaseError(404, f"Event with id {event_id} not found!")

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    if found_admin.org_id != found_event.org_id:
        raise DatabaseError(403, "Authenticated admin not apart of organization!")

    try:
        new_event = update_event_helper(found_event, event_updates)
    except ValueError as exc:
        raise DatabaseError(400, f"Error updating database event! {exc}")

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
    db.refresh(new_event)
    return new_event


def delete_org_event(db: Session, event_id: int, admin_id: int):

    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        raise DatabaseError(404, f"Event with id {event_id} not found!")

    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        raise DatabaseError(404, f"Admin with id {admin_id} not found!")

    if found_event.org_id != found_admin.org_id:
        raise DatabaseError(403, "Authenticated admin not apart of organization!")

    db.delete(found_event)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DatabaseError(500, f"An error occured commiting to database! {exc}")
