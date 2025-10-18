from typing import Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...models import dbmodels, models


# Example repo-style usage
def create_volunteer(db: Session, new_volunteer: models.VolunteerCreate):

    vol = dbmodels.Volunteer(
        email=new_volunteer.email,
        password=new_volunteer.password,
        first_name=new_volunteer.first_name,
        last_name=new_volunteer.last_name,
        description=new_volunteer.description,
        image_url=new_volunteer.image_url,
        location=new_volunteer.location,
    )

    skills: Iterable[str] = getattr(new_volunteer, "skills", None) or []
    for s in {s.strip() for s in skills if s and s.strip()}:
        vol.skills.append(dbmodels.VolunteerSkill(skill=s))

    db.add(vol)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(vol)
    return vol


# CREATE OrgAdmin obj
# Check the obj for expected params ^^^
def create_org_admin(db: Session, new_admin: models.AdminCreate):

    admin = dbmodels.OrgAdmin(
        email=new_admin.email,
        password=new_admin.password,
        first_name=new_admin.first_name,
        last_name=new_admin.last_name,
        description=new_admin.description,
        image_url=new_admin.image_url,
    )

    db.add(admin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(admin)
    return admin


def get_volunteer_login(db: Session, email: str):
    query = select(dbmodels.Volunteer).where(dbmodels.Volunteer.email == email)

    volunteer_login = db.execute(query).scalar_one_or_none()

    return volunteer_login


def get_admin_login(db: Session, email: str):
    query = select(dbmodels.OrgAdmin).where(dbmodels.OrgAdmin.email == email)

    admin_login = db.execute(query).scalar_one_or_none()

    return admin_login


def get_current_volunteer(db: Session, id: int):
    query = select(dbmodels.Volunteer).where(dbmodels.Volunteer.id == id)

    current_volunteer = db.execute(query).scalar_one_or_none()

    return current_volunteer


def get_current_admin(db: Session, id: int):
    query = select(dbmodels.OrgAdmin).where(dbmodels.OrgAdmin.id == id)

    current_admin = db.execute(query).scalar_one_or_none()

    return current_admin


def get_event(db: Session, id: int):
    query = select(dbmodels.Event).where(dbmodels.Event.id == id)

    event = db.execute(query).scalar_one_or_none()

    return event


def create_event(db: Session, event: models.EventCreate, id: int):

    admin = get_current_admin(db, id)

    if admin is None:
        return None

    new_event = dbmodels.Event(
        name=event.name,
        description=event.description,
        location=event.description,
        urgency=event.urgency,
        capacity=event.capacity,
    )

    skills: Iterable[str] = getattr(new_event, "needed_skills", None) or []
    for s in {s.strip() for s in skills if s and s.strip()}:
        new_event.needed_skills.append(dbmodels.EventSkill(skill=s))

    db.add(new_event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(new_event)
    return new_event
