from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.pydanticmodels import OrgCreate, OrgUpdate
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    get_org_from_id,
    get_current_admin,
    create_new_org,
    org_admin_signup,
    delete_org,
    update_org,
)

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/{org_id}")
async def get_org_details(org_id: int, db: Session = Depends(get_db)):

    org = get_org_from_id(db, org_id)

    if org is None:
        raise HTTPException(404, f"Organization with id {org_id} not found!")

    return org


# Must be authed as an org admin
# Also, must attach org admin id to user
@router.post("/create")
async def create_org(
    org: OrgCreate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:

        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin")

        found_admin = get_current_admin(db, user_info.user_id)

        if found_admin is None:
            raise HTTPException(404, "Authenticated admin not found in database!")

        new_org = create_new_org(db, org)

        # We wanna sign up the person who made the organization
        if not org_admin_signup(db, new_org.id, found_admin.id):
            raise HTTPException(500, "Database error")

        return new_org

    except HTTPException as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be created. {exc.detail}"
        )


@router.patch("/{org_id}")
async def update_org_from_id(
    org_id: int,
    org_updates: OrgUpdate,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin")

        found_admin = get_current_admin(db, user_info.user_id)

        if found_admin is None:
            raise HTTPException(404, "Authenticated admin not found in database!")

        found_org = get_org_from_id(db, org_id)

        if found_org is None:
            raise HTTPException(404, f"Organization with id '{org_id}' not found!")

        if found_admin.org_id != found_org.id:
            raise HTTPException(403, "Admin is not apart of organization!")

        new_org = update_org(db, found_org, org_updates)

        return new_org

    except HTTPException as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be updated. {exc.detail}"
        )


@router.delete("/{org_id}")
async def delete_org_from_id(
    org_id: int,
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin")

        found_admin = get_current_admin(db, user_info.user_id)

        if found_admin is None:
            raise HTTPException(404, "Authenticated admin not found in database!")

        found_org = get_org_from_id(db, org_id)

        if found_org is None:
            raise HTTPException(404, f"Organization with id '{org_id}' not found!")

        if found_admin.org_id != found_org.id:
            raise HTTPException(403, "Admin is not apart of organization!")

        if not delete_org(db, found_org):
            raise HTTPException(500, "Database error when deleting")

        return {"message": f"Event successfully deleted!"}

    except HTTPException as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be deleted. {exc.detail}"
        )
