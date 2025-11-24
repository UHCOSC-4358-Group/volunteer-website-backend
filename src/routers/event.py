from fastapi import APIRouter, Depends, status, Body, File, Form, UploadFile
from sqlalchemy.orm import Session
from mypy_boto3_s3 import S3Client
from ..models import dbmodels
from ..models.pydanticmodels import EventCreate, EventUpdate
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin, is_volunteer
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    create_org_event,
    update_org_event,
    delete_org_event,
    get_event_from_id,
)
from ..dependencies.database.relations import (
    signup_volunteer_event,
    remove_volunteer_event,
    match_volunteers_to_event,
)
from ..dependencies.aws import upload_image, get_s3
from ..dependencies.geocoding import get_coordinates
from ..util import error

router = APIRouter(prefix="/events", tags=["event"])


# CRITERIA: None, anyone can retrieve event data
@router.get("/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    found_event = get_event_from_id(db, event_id)

    if found_event is None:
        raise error.NotFoundError("event", event_id)

    return found_event


# CRITERIA: MUST BE AUTHED, AND MUST BE AN ADMIN
@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: str = Form(...),
    image: UploadFile | None = File(default=None),
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    event = EventCreate.model_validate_json(event_data)
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    latlong: tuple[float, float] | None = None
    if event.location is not None:
        latlong = get_coordinates(event.location)

    image_url: str | None = None
    if image is not None:
        image_url = upload_image(s3, image)

    new_event = create_org_event(db, event, admin_id, image_url, latlong)

    return new_event


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER
@router.patch("/{event_id}")
async def update_event(
    event_id: int,
    event_updates_data: str = Form(...),
    image: UploadFile | None = File(default=None),
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):

    event_updates = EventUpdate.model_validate_json(event_updates_data)
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    latlong: tuple[float, float] | None = None
    if event_updates.location is not None:
        latlong = get_coordinates(event_updates.location)

    image_url: str | None = None
    if image is not None:
        image_url = upload_image(s3, image)

    updated_event = update_org_event(
        db, event_id, event_updates, admin_id, image_url, latlong
    )

    return updated_event


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    # DB function handles authorization through org_id
    delete_org_event(db, event_id, admin_id)

    return {"message": "Event deleted successfully!"}


@router.post("/{event_id}/signup", status_code=status.HTTP_201_CREATED)
async def event_volunteer_signup(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_volunteer(user_info):
        raise error.AuthorizationError("User is not a volunteer")

    vol_id = user_info.user_id

    signup_volunteer_event(db, vol_id, event_id)

    return {"message": "Volunteer has been signed up to event"}


@router.delete("/{event_id}/dropout")
async def event_volunteer_delete(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_volunteer(user_info):
        raise error.AuthorizationError("User is not an admin")

    vol_id = user_info.user_id

    remove_volunteer_event(db, vol_id, event_id)

    return {"message": "Volunteer has been disenrolled from event"}


@router.get("/{event_id}/match")
async def event_volunteer_matching(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    matched_results = match_volunteers_to_event(db, event_id, admin_id)

    volunteers: list[dbmodels.Volunteer] = []
    for volunteer, _ in matched_results:
        volunteers.append(volunteer)

    return volunteers
