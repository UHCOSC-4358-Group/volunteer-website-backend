from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..models.pydanticmodels import EventCreate, EventUpdate
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin, is_volunteer
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    get_current_admin,
    create_org_event,
    update_org_event,
    delete_org_event,
    get_event_from_id,
)
from ..dependencies.database.relations import (
    signup_volunteer_event,
    remove_volunteer_event,
    get_event_volunteer,
)
from ..util.error import DatabaseError

router = APIRouter(prefix="/events", tags=["event"])


# CRITERIA: None, anyone can retrieve event data
@router.get("/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    try:
        found_event = get_event_from_id(db, event_id)

        if found_event is None:
            raise HTTPException(404, f"Event with id {event_id} not found!")

        return found_event
    except (HTTPException, DatabaseError) as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be retrieved. {exc.detail}"
        )


# CRITERIA: MUST BE AUTHED, AND MUST BE AN ADMIN
@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # User_id must be an admin, and must be in that org
        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin!")

        found_admin = get_current_admin(db, user_info.user_id)

        if found_admin is None:
            raise HTTPException(403, "Authenticated user not found!")

        if found_admin.org_id != event.org_id:
            raise HTTPException(403, "Admin is not part of organization!")

        new_event = create_org_event(db, event)

        return new_event
    except (HTTPException, DatabaseError) as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be created. {exc.detail}"
        )


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER
@router.patch("/{event_id}")
async def update_event(
    event_id: int,
    event_updates: EventUpdate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # User_id must be an admin, and must be in that org
        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin!")

        found_admin = get_current_admin(db, user_info.user_id)

        if found_admin is None:
            raise HTTPException(403, "Authenticated user not found!")

        found_event = get_event_from_id(db, event_id)

        if found_event is None:
            raise HTTPException(404, "Event not found!")

        if found_admin.org_id != found_event.org_id:
            raise HTTPException(403, "Admin is not part of organization!")

        updated_event = update_org_event(db, found_event, event_updates)

        return updated_event
    except (HTTPException, DatabaseError) as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be updated. {exc.detail}"
        )


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # User_id must be an admin, and must be in that org
        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin!")

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

        delete_org_event(db, found_event)

        return {"message": "Event deleted successfully!"}
    except (HTTPException, DatabaseError) as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be deleted. {exc.detail}"
        )


# TODO: Create endpoint for assigning volunteer to event
@router.post("/{event_id}/signup", status_code=status.HTTP_201_CREATED)
async def event_volunteer_signup(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not is_volunteer(user_info):
            raise HTTPException(403, "User is not volunteer!")

        signup_volunteer_event(db, user_info.user_id, event_id)

        return {"message": "Volunteer has been signed up to event!"}

    except (HTTPException, DatabaseError) as exc:
        raise HTTPException(
            exc.status_code,
            detail=f"Volunteer could not be signed up to event. {exc.detail}",
        )


@router.delete("/{event_id}/dropout")
async def event_volunteer_delete(
    event_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not is_volunteer(user_info):
            raise HTTPException(403, "User is not volunteer!")

        found_event_volunteer = get_event_volunteer(db, user_info.user_id, event_id)

        if found_event_volunteer is None:
            raise HTTPException(404, "Volunteer is not signed up to event!")

        remove_volunteer_event(
            db, found_event_volunteer.volunteer.id, found_event_volunteer.event.id
        )

        return {"message": "Volunteer has been disenrolled from event"}

    except (HTTPException, DatabaseError) as exc:
        raise HTTPException(
            exc.status_code,
            detail=f"Volunteer could not be deleted from event. {exc.detail}",
        )
