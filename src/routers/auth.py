from fastapi import (
    APIRouter,
    Response,
    Depends,
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
from ..dependencies.geocoding import get_coordinates
from ..util import error

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/vol/signup", status_code=status.HTTP_201_CREATED)
async def volunteer_signup(
    response: Response,
    vol_data: str = Form(),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    vol = VolunteerCreate.model_validate_json(vol_data)

    latlong: tuple[float, float] | None = None

    if vol.location is not None:
        latlong = get_coordinates(vol.location)
        print(latlong[0], latlong[1])

    image_url: str | None = None
    if image is not None:
        image_url = upload_image(s3, image)

    vol.password = hash_password(vol.password)

    volunteer_obj = create_volunteer(db, vol, image_url, latlong)

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
        raise error.AuthenticationError("User or password incorrect")

    if not verify_password(login_data.password, found_volunteer.password):
        raise error.AuthenticationError("User or password incorrect")

    sign_JWT_volunteer(found_volunteer.id, response)

    return found_volunteer


@router.post("/org/signup", status_code=status.HTTP_201_CREATED)
async def admin_signup(
    response: Response,
    admin_data: str = Form(...),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    admin = AdminCreate.model_validate_json(admin_data)
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

    # Let's just throw the same error so it's harder to hack the system
    if found_admin is None:
        raise error.AuthenticationError("User or password incorrect")

    if not verify_password(login_data.password, found_admin.password):
        raise error.AuthenticationError("User or password incorrect")

    # Delete password so it isn't passed along
    # del found_admin.password

    sign_JWT_admin(found_admin.id, response)

    return found_admin


@router.get("/vol")
async def get_volunteer(
    user_info: UserTokenInfo = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not is_volunteer(user_info):
        raise error.AuthorizationError("User is not an volunteer")

    found_volunteer = get_current_volunteer(db, user_info.user_id)

    if found_volunteer is None:
        raise error.NotFoundError("volunteer", user_info.user_id)

    return found_volunteer


@router.get("/admin")
async def get_admin(
    user_info: UserTokenInfo = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not is_admin(user_info):
        raise error.AuthorizationError("User is not an admin")

    found_admin = get_current_admin(db, user_info.user_id)

    if found_admin is None:
        raise error.NotFoundError("admin", user_info.user_id)

    return found_admin


@router.get("")
async def get_user(
    user_info: UserTokenInfo = Depends(get_current_user), db: Session = Depends(get_db)
):
    if is_volunteer(user_info):
        return await get_volunteer(user_info, db)
    elif is_admin(user_info):
        return await get_admin(user_info, db)
    else:
        raise error.AuthorizationError("Type of user not recognized")


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out!"}
