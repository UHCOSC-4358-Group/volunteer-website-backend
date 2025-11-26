from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List

from ..models.pydanticmodels import NotificationCreate, NotificationOut
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin, is_volunteer
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    create_notification,
    get_notifications_for_user,
)
from ..util import error


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def send_notification(
    payload: NotificationCreate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Any authenticated user may send a custom notification to a volunteer or admin.
    """

    # creation itself handles recipient validation
    created = create_notification(db, payload)

    return created


@router.get("/", response_model=List[NotificationOut])
async def list_my_notifications(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List notifications for the authenticated user.
    """
    if is_volunteer(user_info):
        user_type = "volunteer"
    elif is_admin(user_info):
        user_type = "admin"
    else:
        raise error.AuthorizationError("Unknown user type")

    notes = get_notifications_for_user(
        db, user_info.user_id, user_type, limit=limit, offset=offset
    )

    # Map DB objects to NotificationOut
    out = []
    for n in notes:
        if user_type == "volunteer":
            rid = n.recipient_volunteer_id
        else:
            rid = n.recipient_admin_id
        if rid is None:
            raise error.ExternalServiceError(
                "Notifications", "Notification wasn't supplied with correct id"
            )

        out.append(
            NotificationOut(
                id=n.id,
                subject=n.subject,
                body=n.body,
                created_at=n.created_at,
                recipient_id=rid,
                recipient_type=user_type,
            )
        )

    return out
