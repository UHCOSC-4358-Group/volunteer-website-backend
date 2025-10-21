from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.models import Org
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import get_org_from_id

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/{org_id}")
async def get_org_details(org_id: int, db: Session = Depends(get_db)):

    org = get_org_from_id(db, org_id)

    if org is None:
        raise HTTPException(404, f"Organization with id {org_id} not found!")

    return org


# Must be authed and must be apart of org attached to orgcreate model
@router.post("/create")
async def create_org():
    ...
    # Create OrgCreate model


# @router.patch("/")
