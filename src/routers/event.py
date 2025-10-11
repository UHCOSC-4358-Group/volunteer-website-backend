from fastapi import APIRouter, Depends
from ..models.models import EventCreate
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/event", tags=["event"])


# TODO: CREATE EVENT READ ENDPOINT
# CRITERIA: None, anyone can retrieve event data
@router.get("/{event_id}")
async def get_event(event_id: str): ...


# TODO: CREATE EVENT CREATION ENDPOINT
# CRITERIA: MUST BE AUTHED, AND MUST BE AN ADMIN
@router.post("/create")
async def create_event(event: EventCreate, user_id=Depends(get_current_user)): ...


# TODO: CREATE EVENT UPDATE ENDPOINT
# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


@router.patch("/{event_id}")
async def update_event(event_id: str, user_id=Depends(get_current_user)): ...


# TODO: CREATE EVENT DELETION ENDPOINT
# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


@router.delete("/{event_id}")
async def delete_event(event_id: str, user_id=Depends(get_current_user)): ...
