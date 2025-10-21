from typing import Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels, pydanticmodels


def get_event_volunteer(db: Session, volunteer_id: int, event_id: int):
    event_volunteer = db.get(dbmodels.EventVolunteer, (volunteer_id, event_id))

    return event_volunteer


# Signs up an admin with an organization
def signup_org_admin(db: Session, org_id: int, admin_id: int):
    found_admin = db.get(dbmodels.OrgAdmin, admin_id)

    if found_admin is None:
        return False

    found_org = db.get(dbmodels.Organization, org_id)

    if found_org is None:
        return False

    found_org.admins.append(found_admin)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def signup_volunteer_event(db: Session, volunteer_id: int, event_id: int):

    found_volunteer = db.get(dbmodels.Volunteer, volunteer_id)

    if found_volunteer is None:
        return False

    found_event = db.get(dbmodels.Event, event_id)

    if found_event is None:
        return False

    new_volunteer_event = dbmodels.EventVolunteer(
        volunteer=found_volunteer, event=found_event
    )

    if found_event.assigned >= found_event.capacity:
        return False

    db.add(new_volunteer_event)

    found_event.assigned += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def remove_volunteer_event(db: Session, volunteer_id: int, event_id: int):
    event_volunteer = db.get(dbmodels.EventVolunteer, (event_id, volunteer_id))

    if event_volunteer is None:
        return False

    event = event_volunteer.event

    if event.assigned < 0:
        return False

    event.assigned -= 1

    db.delete(event_volunteer)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True
