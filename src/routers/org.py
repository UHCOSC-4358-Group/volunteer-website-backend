from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from mypy_boto3_s3 import S3Client
from typing import List, Optional, Dict, Any
from fastapi import Query
from ..models.pydanticmodels import OrgCreate, OrgUpdate
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin, is_volunteer
from ..dependencies.aws import get_s3, upload_image
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    get_org_from_id,
    create_new_org,
    delete_org,
    update_org,
    get_current_admin,
    get_upcoming_events_by_org,
    search_organizations,
    get_org_profile_data,
)
from ..dependencies.geocoding import get_coordinates
from ..util import error
from ..dependencies.database.relations import (
    signup_org_admin,
    get_org_past_volunteers,
    match_volunteers_to_event,
)

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/past-volunteers")
async def get_admin_org_past_volunteers(
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all volunteers who have worked past events for the authenticated admin's organization,
    including the events they worked and the computed hours for each event.
    """
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin = get_current_admin(db, user_info.user_id)
    if admin is None:
        raise error.NotFoundError("admin", user_info.user_id)

    if admin.org_id is None:
        return []

    results = get_org_past_volunteers(db, admin.org_id)

    return results


@router.get("/events")
async def get_admin_org_events(
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return upcoming events for the authenticated admin's organization.
    """
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin = get_current_admin(db, user_info.user_id)
    if admin is None:
        raise error.NotFoundError("admin", user_info.user_id)

    if admin.org_id is None:
        return []

    events = get_upcoming_events_by_org(db, admin.org_id)

    def serialize_event(event):
        location = None
        if getattr(event, "location", None) is not None:
            location = {
                "address": event.location.address,
                "city": event.location.city,
                "state": event.location.state,
                "zip_code": event.location.zip_code,
                "country": event.location.country,
            }

        return {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "day": event.day.isoformat() if event.day else None,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "urgency": (
                event.urgency.value
                if hasattr(event.urgency, "value")
                else str(event.urgency)
            ),
            "capacity": event.capacity,
            "assigned": event.assigned,
            "org_id": event.org_id,
            "location": location,
            "needed_skills": (
                [skill.skill for skill in event.needed_skills]
                if getattr(event, "needed_skills", None)
                else []
            ),
        }

    return [serialize_event(evt) for evt in events]


@router.get("/search")
async def search_orgs(
    q: Optional[str] = Query(
        None, min_length=1, description="Search term (name or description)"
    ),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    results: list[dict[str, Any]] = []
    total: int = 0

    results, total = search_organizations(db, q, city, state, limit, offset)

    return {"count": total, "results": results}


@router.get("/{org_id}")
async def get_org_details(org_id: int, db: Session = Depends(get_db)):

    org = get_org_from_id(db, org_id)

    if org is None:
        raise error.NotFoundError("organization", org_id)

    return org


# Must be authed as an org admin
# Also, must attach org admin id to user
@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_org(
    org_data: str = Form(...),
    image: UploadFile = File(default=None),
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    org = OrgCreate.model_validate_json(org_data)

    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    image_url: str | None = None
    if image is not None:
        image_url = upload_image(s3, image)

    latlong: tuple[float, float] | None = None
    if org.location is not None:
        latlong = get_coordinates(org.location)

    new_org = create_new_org(db, org, admin_id, image_url, latlong)

    return new_org


@router.patch("/{org_id}")
async def update_org_from_id(
    org_id: int,
    org_updates_data: str = Form(...),
    image: UploadFile | None = File(default=None),
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    org_updates = OrgUpdate.model_validate_json(org_updates_data)

    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    image_url: str | None = None
    if image:
        image_url = upload_image(s3, image)

    latlong: tuple[float, float] | None = None

    if org_updates.location is not None:
        latlong = get_coordinates(org_updates.location)

    updated_org = update_org(db, org_id, org_updates, admin_id, image_url, latlong)

    return updated_org


@router.delete("/{org_id}")
async def delete_org_from_id(
    org_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    delete_org(db, org_id, admin_id)

    return {"message": f"Event successfully deleted!"}


@router.get("/admin/{admin_id}")
async def get_admin_profile(
    admin_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get admin details along with their organization and upcoming events.
    """

    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    if user_info.user_id != admin_id:
        raise error.AuthorizationError("Admin can only access their own profile")

    # Get the admin
    found_admin = get_current_admin(db, admin_id)

    if found_admin is None:
        raise error.NotFoundError("admin", admin_id)

    # Get the organization if admin has one
    org_data = None
    upcoming_events = []

    organization = get_org_from_id(db, found_admin.org_id)

    if organization:
        org_data = get_org_profile_data(db, organization.id)

        upcoming_events = get_upcoming_events_by_org(db, organization.id)

    return {
        "admin": found_admin,
        "organization": org_data,
        "upcoming_events": upcoming_events,
    }


@router.post("/{org_id}/signup", status_code=status.HTTP_201_CREATED)
def signup_current_admin_to_org(
    org_id: int,
    db: Session = Depends(get_db),
    user_info: UserTokenInfo = Depends(get_current_user),
):
    # require admin role
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin_id = user_info.user_id

    # signup_org_admin will validate existence/relationship and commit
    signup_org_admin(db, org_id, admin_id)

    return {
        "message": "Admin signed up to organization",
        "org_id": org_id,
        "admin_id": admin_id,
    }


@router.get("/events/match")
async def get_admin_org_event_matches(
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    top_k: int = Query(10, ge=1, le=100),
):
    """
    For the authenticated admin, run volunteer matching for every upcoming
    event in their organization and return the top matches per event.
    """
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    admin = get_current_admin(db, user_info.user_id)
    if admin is None:
        raise error.NotFoundError("admin", user_info.user_id)

    if admin.org_id is None:
        return []

    events = get_upcoming_events_by_org(db, admin.org_id)

    results: List[Dict[str, Any]] = []

    for ev in events:
        matched = match_volunteers_to_event(db, ev.id, admin.user_id)

        # shape matched volunteers: (Volunteer, score)
        matches_list: List[Dict[str, Any]] = []
        for vol, score in matched[:top_k]:
            matches_list.append(
                {
                    "volunteer_id": vol.id,
                    "first_name": vol.first_name,
                    "last_name": vol.last_name,
                    "email": vol.email,
                    "score": float(score),
                }
            )

        results.append(
            {
                "event_id": ev.id,
                "name": ev.name,
                "day": ev.day if ev.day else None,
                "start_time": ev.start_time if ev.start_time else None,
                "end_time": ev.end_time if ev.end_time else None,
                "matches": matches_list,
            }
        )

    return {"org_id": admin.org_id, "count": len(results), "results": results}
