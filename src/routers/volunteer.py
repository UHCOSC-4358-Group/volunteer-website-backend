# src/routers/volunteer.py
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ..dependencies.database.config import get_db
from ..dependencies.auth import get_current_user, is_admin, UserTokenInfo
from ..dependencies.database.relations import (
    match_events_to_volunteer,
    get_volunteer_history,
)
from ..util import error

router = APIRouter(prefix="/vol", tags=["volunteer"])


@router.get("/{volunteer_id}/match")
def volunteer_event_matches(
    volunteer_id: int = Path(..., ge=1),
    top_k: int = Query(10, ge=1, le=100),
    min_score: float = Query(0.15, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    user: UserTokenInfo = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Recommend events for a volunteer.
    - Volunteer may view their own matches.
    - Admin may view any volunteer's matches.
    """
    # authorize
    if user.user_id != volunteer_id or not is_admin(user):
        raise error.AuthorizationError("Current user does not have same id as request")

    # compute matches
    scored = match_events_to_volunteer(db, volunteer_id)

    # shape response
    matches: List[Dict[str, Any]] = []
    for event, score in scored[:top_k]:
        matches.append(
            {
                "event_id": event.id,
                "name": event.name,
                "location": event.location,
                "day": event.day.isoformat() if event.day else None,
                "start_time": (
                    event.start_time.isoformat() if event.start_time else None
                ),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "urgency": str(event.urgency),
                "needed_skills": [s.skill for s in (event.needed_skills or [])],
                "capacity": event.capacity,
                "assigned": event.assigned,
                "score": float(score),
            }
        )

    return {"volunteer_id": volunteer_id, "count": len(matches), "matches": matches}


@router.get("/{volunteer_id}/history")
def volunteer_history(
    volunteer_id: int,
    db: Session = Depends(get_db),
):
    past_events = get_volunteer_history(db, volunteer_id)

    return past_events
