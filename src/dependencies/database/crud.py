from typing import Iterable
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
def create_org_admin(db: Session, new_admin: models.AdminCreate): ...
