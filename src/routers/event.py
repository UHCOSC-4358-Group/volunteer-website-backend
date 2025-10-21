from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..models.models import EventCreate, EventUpdate
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    get_current_admin,
    create_org_event,
    get_event_from_id,
    update_org_event,
    delete_org_event,
)

router = APIRouter(prefix="/events", tags=["event"])


# CRITERIA: None, anyone can retrieve event data
@router.get("/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    found_event = get_event_from_id(db, event_id)

    if found_event is None:
        raise HTTPException(404, f"Event with id {event_id} not found!")

    return found_event


# CRITERIA: MUST BE AUTHED, AND MUST BE AN ADMIN
@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise HTTPException(403, "Event could not be created. User is not an admin!")

    found_admin = get_current_admin(db, user_info.user_id)

    if found_admin is None:
        raise HTTPException(
            403, "Event could not be created. Authenticated user not found!"
        )

    if found_admin.org_id != event.org_id:
        raise HTTPException(
            403, "Event could not be created. Admin is not part of organization!"
        )

    new_event = create_org_event(db, event)

    if new_event is None:
        raise HTTPException(
            400, "Event could not be created. Database could not verify transaction"
        )

    return {"message": f"Event '{new_event.name}' successfully created!"}


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER
@router.patch("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(
    event_id: int,
    event_updates: EventUpdate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise HTTPException(401, "User is not an admin!")

    found_admin = get_current_admin(db, user_info.user_id)

    if found_admin is None:
        raise HTTPException(
            403, "Event could not be updated. Authenticated user not found!"
        )

    found_event = get_event_from_id(db, event_id)

    if found_event is None:
        raise HTTPException(404, "Event could not be updated. Event not found!")

    if found_admin.org_id != found_event.org_id:
        raise HTTPException(
            403, "Event could not be updated. Admin is not part of organization!"
        )

    updated_event = update_org_event(db, found_event, event_updates)

    return {"message": f"Event '{updated_event.name}' updated successfully!"}


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise HTTPException(401, "User is not an admin!")

    found_admin = get_current_admin(db, user_info.user_id)

    if found_admin is None:
        raise HTTPException(
            403, "Event could not be updated. Authenticated user not found!"
        )

    found_event = get_event_from_id(db, event_id)

    if found_event is None:
        raise HTTPException(404, "Event could not be updated. Event not found!")

    if found_admin.org_id != found_event.org_id:
        raise HTTPException(
            403, "Event could not be updated. Admin is not part of organization!"
        )

    if not delete_org_event(db, found_event):
        raise HTTPException(500, "Event could not be deleted. DB error.")

    return {"message": "Event deleted successfully!"}


# TODO: Create endpoint for assigning volunteer to event
@router.post("/{event_id}/signup")
async def event_volunteer_signup(
    event_id: str, user_info: UserTokenInfo = Depends(get_current_user)
): ...
