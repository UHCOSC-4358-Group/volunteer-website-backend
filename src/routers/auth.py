from fastapi import (
    APIRouter,
    Response,
    Depends,
    HTTPException,
    status,
    File,
    Form,
    UploadFile,
)
from pydantic import BaseModel, EmailStr
from mypy_boto3_s3 import S3Client
from ..models.pydanticmodels import VolunteerCreate, AdminCreate
from ..dependencies.auth import (
    hash_password,
    verify_password,
    sign_JWT_volunteer,
    sign_JWT_admin,
    get_current_user,
    is_admin,
    is_volunteer,
    UserTokenInfo,
)
from sqlalchemy.orm import Session
from ..dependencies.database.config import get_db
from ..dependencies.database.crud import (
    create_volunteer,
    create_org_admin,
    get_volunteer_login,
    get_admin_login,
    get_current_volunteer,
    get_current_admin,
)
from ..dependencies.aws import get_s3, upload_image

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/vol/signup", status_code=status.HTTP_201_CREATED)
async def volunteer_signup(
    response: Response,
    vol_str: str = Form(json_schema_extra=VolunteerCreate.model_json_schema()),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):

    # If user uploaded an image, then upload image to aws and return the url
    vol = VolunteerCreate.model_validate_json(vol_str)

    image_url: str | None = None
    if image is not None:
        image_url = upload_image(s3, image)

    vol.password = hash_password(vol.password)

    volunteer_obj = create_volunteer(db, vol, image_url)

    sign_JWT_volunteer(volunteer_obj.id, response)

    return volunteer_obj


class LoginData(BaseModel):
    email: EmailStr
    password: str


@router.post("/vol/login")
async def volunteer_login(
    login_data: LoginData, response: Response, db: Session = Depends(get_db)
):
    found_volunteer = get_volunteer_login(db, login_data.email)

    if found_volunteer is None:
        raise HTTPException(401, "User email or password incorrect!")

    if not verify_password(login_data.password, found_volunteer.password):
        raise HTTPException(401, "User or password incorrect!")

    del found_volunteer.password

    sign_JWT_volunteer(found_volunteer.id, response)

    return found_volunteer


@router.post("/org/signup", status_code=status.HTTP_201_CREATED)
async def admin_signup(
    response: Response,
    admin_str: str = Form(json_schema_extra=AdminCreate.model_json_schema()),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    admin = AdminCreate.model_validate_json(admin_str)
    image_url: str | None = None
    if image is not None:
        image_url = upload_image(s3, image)

    admin.password = hash_password(admin.password)
    admin_obj = create_org_admin(db, admin, image_url)
    sign_JWT_admin(admin_obj.id, response)
    return admin_obj


@router.post("/org/login")
async def admin_login(
    login_data: LoginData, response: Response, db: Session = Depends(get_db)
):
    found_admin = get_admin_login(db, login_data.email)

    if found_admin is None:
        raise HTTPException(401, "User or password incorrect!")

    if not verify_password(login_data.password, found_admin.password):
        raise HTTPException(401, "User or password incorrect!")

    # Delete password so it isn't passed along
    del found_admin.password

    sign_JWT_admin(found_admin.id, response)

    return found_admin


@router.get("/vol")
async def get_volunteer(
    user_info: UserTokenInfo = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not is_volunteer(user_info):
        raise HTTPException(403, detail="User is not a volunteer!")

    found_volunteer = get_current_volunteer(db, user_info.user_id)

    if found_volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found!")

    return found_volunteer


@router.get("/admin")
async def get_admin(
    user_info: UserTokenInfo = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not is_admin(user_info):
        raise HTTPException(403, detail="User is not an admin!")

    found_admin = get_current_admin(db, user_info.user_id)

    if found_admin is None:
        raise HTTPException(status_code=404, detail="Organization admin not found!")

    return found_admin


@router.get("")
async def get_user(
    user_info: UserTokenInfo = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        if is_volunteer(user_info):
            return await get_volunteer(user_info, db)
        elif is_admin(user_info):
            return await get_admin(user_info, db)
        else:
            raise HTTPException(403, "User type not recognized!")
    except HTTPException as exc:
        raise HTTPException(
            exc.status_code, f"Could not retrieve user info! {exc.detail}"
        )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out!"}
