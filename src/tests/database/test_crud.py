from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from unittest.mock import patch
import pytest
from src.dependencies.database import crud
from src.models import pydanticmodels, dbmodels
from src.util import error
from src.tests.database.conftest import Factories
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
def test_create_volunteer_with_integrity_error(db_session: Session):

    org_admin = admin.build(first_name="Ricky")

    # Simulates Integrity Error and checks for Database Error
    with patch.object(
        db_session,
        "commit",
        side_effect=IntegrityError("stmt", "params", RuntimeError()),
    ):
        with pytest.raises(error.DatabaseOperationError):
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


def test_create_new_org(db_session: Session, factories: Factories):

    NAME = "ORG"

    admin_obj = factories.admin()

    org_create = org.build(name=NAME)

    db_org = crud.create_new_org(db_session, org_create, admin_obj.id)

    assert db_org.name == NAME

    # Fake admin Id
    FAKE_ADMIN_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.create_new_org(db_session, org_create, FAKE_ADMIN_ID)

    assert exc.value.status_code == 404


def test_delete_org(db_session: Session, factories: Factories):

    db_org = factories.organization()
    admin_obj = factories.admin(org_id=db_org.id)

    org_id = db_org.id

    crud.delete_org(db_session, org_id, admin_obj.id)

    assert crud.get_org_from_id(db_session, org_id) is None

    db_org = factories.organization()
    admin_obj = factories.admin(org_id=db_org.id)

    org_id = db_org.id

    # Fake admin id
    FAKE_ADMIN_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.delete_org(db_session, org_id, FAKE_ADMIN_ID)

    assert exc.value.status_code == 404

    # Fake org id
    FAKE_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.delete_org(db_session, FAKE_ID, admin_obj.id)

    assert exc.value.status_code == 404

    # Non authorized admin
    non_auth_admin = factories.admin()
    with pytest.raises(error.AuthorizationError) as exc:
        crud.delete_org(db_session, org_id, non_auth_admin.id)

    assert exc.value.status_code == 403


def test_update_org_helper(db_session: Session, factories: Factories):

    # First, let's check that no changes are made if we pass in None
    org_obj_1 = factories.organization()

    old_org_name_1 = org_obj_1.name
    old_org_location_1 = org_obj_1.location
    old_org_description_1 = org_obj_1.description
    old_org_image_url_1 = org_obj_1.image_url

    org_updates_1 = pydanticmodels.OrgUpdate(
        name=None, description=None, location=None, image_url=None
    )

    new_org_1 = crud.update_org_helper(org_obj_1, org_updates_1)

    assert new_org_1.name == old_org_name_1
    assert new_org_1.location == old_org_location_1
    assert new_org_1.description == old_org_description_1
    assert new_org_1.image_url == old_org_image_url_1

    org_obj_2 = factories.organization()

    NAME = "Org"
    LOCATION = "San Antonio"

    old_org_description_2 = org_obj_2.description
    old_org_image_url_2 = org_obj_2.image_url

    org_updates_2 = pydanticmodels.OrgUpdate(
        name=NAME, location=LOCATION, description=None, image_url=None
    )

    new_org_2 = crud.update_org_helper(org_obj_2, org_updates_2)

    assert new_org_2.name == NAME
    assert new_org_2.location == LOCATION
    assert new_org_2.description == old_org_description_2
    assert new_org_2.image_url == old_org_image_url_2


def test_update_org(db_session: Session, factories: Factories):
    NAME = "SUPERORG"
    IMAGE_URL = "EXAMPLE.COM/image_url"
    FAKE_ID = -5

    db_org = factories.organization()
    admin_obj = factories.admin(org_id=db_org.id)

    org_id = db_org.id
    old_org_location = db_org.location
    old_org_description = db_org.description

    org_updates = pydanticmodels.OrgUpdate(
        name=NAME, image_url=IMAGE_URL, location=None, description=None
    )

    updated_org = crud.update_org(db_session, org_id, org_updates, admin_obj.id)

    assert updated_org.name == NAME
    assert updated_org.image_url == IMAGE_URL
    assert updated_org.location == old_org_location
    assert updated_org.description == old_org_description

    # Fake org id
    FAKE_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.update_org(db_session, FAKE_ID, org_updates, admin_obj.id)

    assert exc.value.status_code == 404

    # Fake admin id
    ADMIN_FAKE_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.update_org(db_session, org_id, org_updates, ADMIN_FAKE_ID)

    assert exc.value.status_code == 404

    # Non authorized admin
    non_auth_admin = factories.admin()
    with pytest.raises(error.AuthorizationError) as exc:
        crud.update_org(db_session, org_id, org_updates, non_auth_admin.id)

    assert exc.value.status_code == 403


def test_get_event_from_id(db_session: Session, factories: Factories):
    FAKE_ID = -5

    org = factories.organization()
    org_event = factories.event(org=org)

    assert crud.get_event_from_id(db_session, org_event.id) == org_event

    assert crud.get_event_from_id(db_session, FAKE_ID) is None


def test_create_org_event(db_session: Session, factories: Factories):
    org_obj = factories.organization()
    admin_obj = factories.admin()

    admin_obj.organization = org_obj

    db_session.commit()
    db_session.refresh(org_obj)
    db_session.refresh(admin_obj)

    event_create_obj = event.build(org_id=org_obj.id, needed_skills=["Cooking"])

    new_event: dbmodels.Event = crud.create_org_event(
        db_session, event_create_obj, admin_obj.id
    )

    db_session.refresh(org_obj)

    assert org_obj.events[0] is new_event
    assert "Cooking" == new_event.needed_skills[0].skill
    assert new_event.organization is org_obj
    assert len(new_event.volunteers) == 0

    # Fake admin id
    ADMIN_FAKE_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.create_org_event(db_session, event_create_obj, ADMIN_FAKE_ID)

    assert exc.value.status_code == 404

    # Admin not apart of org
    non_auth_admin = factories.admin()
    with pytest.raises(error.AuthorizationError) as exc:
        crud.create_org_event(db_session, event_create_obj, non_auth_admin.id)

    assert exc.value.status_code == 403

    # Fake organization id
    ORGANIZATION_FAKE_ID = -5
    fake_org_create = event.build(org=ORGANIZATION_FAKE_ID)
    with pytest.raises(error.NotFoundError) as exc:
        crud.create_org_event(db_session, fake_org_create, ORGANIZATION_FAKE_ID)

    assert exc.value.status_code == 404


def test_update_event_helper(db_session: Session, factories: Factories):
    org_obj = factories.organization()
    admin_obj = factories.admin(org_id=org_obj.id)
    event_obj = factories.event(org=org_obj)

    old_event_description = event_obj.description

    NAME = "ORG"
    REQUIRED_SKILLS = ["Cleaning", "Cooking"]

    event_updates_obj = pydanticmodels.EventUpdate(
        name=NAME,
        required_skills=REQUIRED_SKILLS,
        description=None,
        location=None,
        urgency=None,
        capacity=None,
    )

    updated_event = crud.update_event_helper(event_obj, event_updates_obj)

    assert updated_event.name == NAME
    assert updated_event.description == old_event_description
    assert any([skill.skill == "Cleaning" for skill in updated_event.needed_skills])
    assert any([skill.skill == "Cooking" for skill in updated_event.needed_skills])

    # Set capacity greater than assigned volunteers
    capacity_event = factories.event(capacity=10, assigned=5)

    event_updates_obj = pydanticmodels.EventUpdate(
        name=None,
        required_skills=None,
        description=None,
        location=None,
        urgency=None,
        capacity=4,
    )

    with pytest.raises(ValueError) as exc:
        crud.update_event_helper(capacity_event, event_updates_obj)

    assert (
        exc.value.args[0]
        == "Capacity cannot be less than currently assigned volunteers"
    )


def test_update_org_event(db_session: Session, factories: Factories):
    event_org = factories.organization()
    org_admin = factories.admin(org_id=event_org.id)
    event_to_be_updated = factories.event(org=event_org)

    UPDATED_NAME = "ORG"
    UPDATED_DESCRIPTION = "ORGANIZATION"

    location = event_to_be_updated.location

    event_updates_obj = pydanticmodels.EventUpdate(
        name=UPDATED_NAME,
        required_skills=None,
        description=UPDATED_DESCRIPTION,
        location=None,
        urgency=None,
        capacity=None,
    )

    updated_event: dbmodels.Event = crud.update_org_event(
        db_session, event_to_be_updated.id, event_updates_obj, org_admin.id
    )

    assert updated_event.name == UPDATED_NAME
    assert updated_event.description == UPDATED_DESCRIPTION
    assert updated_event.location == location

    # Fake event id
    EVENT_FAKE_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.update_org_event(
            db_session, EVENT_FAKE_ID, event_updates_obj, org_admin.id
        )

    assert exc.value.status_code == 404

    # Fake admin id
    ADMIN_FAKE_ID = -5
    with pytest.raises(error.NotFoundError) as exc:
        crud.update_org_event(
            db_session, event_to_be_updated.id, event_updates_obj, ADMIN_FAKE_ID
        )

    assert exc.value.status_code == 404

    # Admin not apart of org
    non_auth_admin = factories.admin()
    with pytest.raises(error.AuthorizationError) as exc:
        crud.update_org_event(
            db_session, event_to_be_updated.id, event_updates_obj, non_auth_admin.id
        )

    assert exc.value.status_code == 403


def test_delete_org_event(db_session: Session, factories: Factories):
    event_org = factories.organization()
    org_admin = factories.admin(org_id=event_org.id)
    event_to_be_deleted = factories.event(org=event_org)

    crud.delete_org_event(db_session, event_to_be_deleted.id, org_admin.id)

    assert crud.get_event_from_id(db_session, event_to_be_deleted.id) is None

    # New event for further testing
    event_to_be_deleted = factories.event(org=event_org)

    # Fake event id
    EVENT_FAKE_ID = -5

    with pytest.raises(error.NotFoundError) as exc:
        crud.delete_org_event(db_session, EVENT_FAKE_ID, org_admin.id)

    assert exc.value.status_code == 404

    # Fake admin id
    ADMIN_FAKE_ID = -5

    with pytest.raises(error.NotFoundError) as exc:
        crud.delete_org_event(db_session, event_to_be_deleted.id, ADMIN_FAKE_ID)

    assert exc.value.status_code == 404

    # Admin not apart of org
    not_auth_admin = factories.admin()

    with pytest.raises(error.AuthorizationError) as exc:
        crud.delete_org_event(db_session, event_to_be_deleted.id, not_auth_admin.id)

    assert exc.value.status_code == 403
