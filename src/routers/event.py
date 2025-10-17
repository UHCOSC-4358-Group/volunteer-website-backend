from fastapi import APIRouter, Depends, HTTPException, status
from ..models.models import EventCreate, Event, EventUpdate, UrgencyLevel
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin
from uuid import uuid4


EVENT_DUMMY_DATA: list[Event] = [
    Event(
        id="evt-550e8400-e29b-41d4-a716-446655440001",
        name="Community Food Drive Setup",
        description="Help set up tables, sort donations, and organize food items for weekend distribution to local families in need.",
        location="Austin Community Center, 123 Main St, Austin, TX",
        required_skills=["Event Planning", "Food Service", "Heavy Lifting"],
        urgency=UrgencyLevel.MEDIUM,
        assigned=3,
        capacity=8,
        org_id="1",
    ),
    Event(
        id="evt-550e8400-e29b-41d4-a716-446655440002",
        name="Emergency Disaster Relief",
        description="Urgent response needed for flood relief efforts including cleanup, supply distribution, and temporary shelter assistance.",
        location="Emergency Response Center, Houston, TX",
        required_skills=[
            "First Aid",
            "Crisis Management",
            "Heavy Lifting",
            "Transportation",
        ],
        urgency=UrgencyLevel.CRITICAL,
        assigned=2,
        capacity=15,
        org_id="2",
    ),
    Event(
        id="evt-550e8400-e29b-41d4-a716-446655440003",
        name="Youth Coding Workshop",
        description="Teach basic programming concepts to middle school students using interactive games and projects.",
        location="Seattle Public Library, Tech Center Room",
        required_skills=["Programming", "Teaching", "Patience with Kids"],
        urgency=UrgencyLevel.LOW,
        assigned=1,
        capacity=4,
        org_id="3",
    ),
]

router = APIRouter(prefix="/events", tags=["event"])


# CRITERIA: None, anyone can retrieve event data
@router.get("/{event_id}")
async def get_event(event_id: str):
    found_events = [event for event in EVENT_DUMMY_DATA if event_id == event.id]
    if len(found_events) == 0:
        raise HTTPException(404, "Event not found!")

    found_event = found_events[0]

    return found_event


# CRITERIA: MUST BE AUTHED, AND MUST BE AN ADMIN
@router.post("/create/{org_id}", status_code=status.HTTP_201_CREATED)
async def create_event(
    org_id: str,
    event: EventCreate,
    user_info: UserTokenInfo = Depends(get_current_user),
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise HTTPException(401, "User is not an admin!")

    # TODO: Check if admin belongs to organization
    # SELECT id FROM users WHERE org_id == users.org_id smth like that

    new_event = Event(
        id=str(uuid4()),
        name=event.name,
        description=event.description,
        location=event.location,
        required_skills=event.required_skills,
        urgency=event.urgency,
        capacity=event.capacity,
        assigned=event.capacity,
        org_id=org_id,
    )

    EVENT_DUMMY_DATA.append(new_event)

    return {"message": "Event successfully created!"}


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


# Handles logic for updating event object
def update_event_helper(old_event: Event, event_updates: EventUpdate) -> Event:
    if event_updates.name is not None:
        old_event.name = event_updates.name

    if event_updates.description is not None:
        old_event.description = event_updates.description

    if event_updates.location is not None:
        old_event.location = event_updates.location

    if event_updates.required_skills is not None:
        old_event.required_skills = event_updates.required_skills

    if event_updates.urgency is not None:
        old_event.urgency = event_updates.urgency

    if event_updates.capacity is not None:
        if event_updates.capacity < old_event.assigned:
            raise ValueError(
                "Capacity cannot be less than currently assigned volunteers"
            )
        old_event.capacity = event_updates.capacity

    if event_updates.assigned is not None:
        old_event.assigned = event_updates.assigned

    return Event.model_validate(old_event)


@router.patch("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(
    event_id: str,
    event_updates: EventUpdate,
    user_info: UserTokenInfo = Depends(get_current_user),
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise HTTPException(401, "User is not an admin!")

    # TODO: Check if admin belongs to organization
    # SELECT id FROM users WHERE org_id == users.org_id smth like that

    found_events = [event for event in EVENT_DUMMY_DATA if event.id == event_id]

    if len(found_events) == 0:
        raise HTTPException(404, detail="Event not found!")

    found_event = found_events[0]

    updated_event = update_event_helper(found_event, event_updates)

    print(updated_event)

    return {"message": "Event updated successfully!"}


# CRITERIA: MUST BE AUTHED, AND ADMIN MUST BE APART OF ORG THAT EVENT IS UNDER


@router.delete("/{event_id}")
async def delete_event(
    event_id: str, user_info: UserTokenInfo = Depends(get_current_user)
):
    # User_id must be an admin, and must be in that org
    if not is_admin(user_info):
        raise HTTPException(401, "User is not an admin!")

    # TODO: Check if admin belongs to organization
    # SELECT id FROM users WHERE org_id == users.org_id smth like that

    index = -1
    for idx, event in enumerate(EVENT_DUMMY_DATA):
        if event_id == event.id:
            index = idx

    if index == -1:
        raise HTTPException(404, "Event not found!")

    EVENT_DUMMY_DATA.pop(index)

    return {"message": "Event deleted successfully!"}


# TODO: Create endpoint for assigning volunteer to event
@router.post("/{event_id}/signup")
async def event_volunteer_signup(
    event_id: str, user_info: UserTokenInfo = Depends(get_current_user)
): ...
