from typing import Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels
from ...util.error import DatabaseError


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
