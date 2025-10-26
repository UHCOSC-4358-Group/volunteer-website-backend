from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from mypy_boto3_s3 import S3Client
from ..models.pydanticmodels import OrgCreate, OrgUpdate
from ..dependencies.auth import get_current_user, UserTokenInfo, is_admin
from ..dependencies.aws import get_s3, upload_image
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    get_org_from_id,
    create_new_org,
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
@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_org(
    org_str: str = Form(json_schema_extra=OrgCreate.model_json_schema()),
    image: UploadFile = File(default=None),
    user_info: UserTokenInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    try:
        org = OrgCreate.model_validate_json(org_str)

        image_url: str | None = None
        if image is not None:
            image_url = upload_image(s3, image)

        if not is_admin(user_info):
            raise HTTPException(403, "User is not an admin")

        admin_id = user_info.user_id

        new_org = create_new_org(db, org, admin_id, image_url)

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

        admin_id = user_info.user_id

        updated_org = update_org(db, org_id, org_updates, admin_id)

        return updated_org

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

        admin_id = user_info.user_id

        delete_org(db, org_id, admin_id)

        return {"message": f"Event successfully deleted!"}

    except HTTPException as exc:
        raise HTTPException(
            exc.status_code, detail=f"Event could not be deleted. {exc.detail}"
        )
