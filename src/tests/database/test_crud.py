from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from unittest.mock import patch
import pytest
from src.dependencies.database import crud
from src.models import pydanticmodels, dbmodels
from src.util.error import DatabaseError
from conftest import Factories
from src.tests.factories.pydantic_factories import volunteer, event, admin, org


def test_create_volunteer(db_session: Session):

    vol_skills = ["Cleaning", "Cooking"]

    vol = volunteer.build(first_name="Ricky", last_name="Trevizo", skills=vol_skills)

    # Create new volunteer
    db_vol = crud.create_volunteer(db_session, vol)

    assert db_vol is not None
    assert db_vol.first_name == "Ricky"
    assert db_vol.last_name == "Trevizo"
    assert any(["Cleaning" == skill.skill for skill in db_vol.skills])
    assert any(["Cooking" == skill.skill for skill in db_vol.skills])


# Only check for integrity error
def test_create_volunteer_with_integrity_erro(db_session: Session):

    org_admin = admin.build(first_name="Ricky")

    # Simulates Integrity Error and checks for Database Error
    with patch.object(
        db_session,
        "commit",
        side_effect=IntegrityError("stmt", "params", RuntimeError()),
    ):
        with pytest.raises(DatabaseError):
            crud.create_org_admin(db_session, org_admin)

    # Check that db rolled back correctly by checking if admin is in db
    query = select(dbmodels.OrgAdmin).where(dbmodels.OrgAdmin.first_name == "Ricky")

    found_admin: dbmodels.OrgAdmin | None = db_session.execute(
        query
    ).scalar_one_or_none()

    assert found_admin is None


def test_create_org_admin(db_session: Session):

    org_admin = admin.build(first_name="org", last_name="admin")

    db_admin = crud.create_org_admin(db_session, org_admin)

    assert db_admin is not None
    assert db_admin.first_name == "org"
    assert db_admin.last_name == "admin"


def test_get_volunteer_login(db_session: Session, factories: Factories):

    EMAIL = "superduper@gmail.com"
    FIRST_NAME = "super"

    # Creates new volunteer with email and adds to db
    factories.volunteer(email=EMAIL, first_name=FIRST_NAME)

    found_vol = crud.get_volunteer_login(db_session, EMAIL)

    assert found_vol is not None
    assert found_vol.email == EMAIL
    assert found_vol.first_name == FIRST_NAME


def test_get_admin_login(db_session: Session, factories: Factories):

    EMAIL = "superadmin@gmail.com"
    FIRST_NAME = "super"

    # Creates new admin with email and adds to db
    factories.admin(email=EMAIL, first_name=FIRST_NAME)

    found_admin = crud.get_admin_login(db_session, EMAIL)

    assert found_admin is not None
    assert found_admin.email == EMAIL
    assert found_admin.first_name == FIRST_NAME


def test_get_current_volunteer(db_session: Session, factories: Factories):
    FIRST_NAME = "super"
    LAST_NAME = "duper"
    db_vol = factories.volunteer(first_name=FIRST_NAME, last_name=LAST_NAME)

    found_vol = crud.get_current_volunteer(db_session, db_vol.id)

    assert found_vol == db_vol


def test_get_current_admin(db_session: Session, factories: Factories):
    FIRST_NAME = "super"
    LAST_NAME = "duper"
    db_admin = factories.admin(first_name=FIRST_NAME, last_name=LAST_NAME)

    found_admin = crud.get_current_admin(db_session, db_admin.id)

    assert found_admin == db_admin


def test_get_org_from_id(db_session: Session, factories: Factories):
    NAME = "Org"

    db_org = factories.organization(name=NAME)

    found_org = crud.get_org_from_id(db_session, db_org.id)

    assert found_org == db_org


def test_create_new_org(db_session: Session):

    NAME = "ORG"

    org_create = org.build(name=NAME)

    db_org = crud.create_new_org(db_session, org_create)

    assert db_org.name == NAME


def test_delete_org(db_session: Session, factories: Factories):

    NAME = "SUPERORG"
    IMAGE_URL = "EXAMPLE.COM/image_url"

    db_org = factories.organization(name=NAME, image_url=IMAGE_URL)
