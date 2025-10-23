from fastapi import APIRouter, Response, Depends, HTTPException
from pydantic import BaseModel, EmailStr
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

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/vol/signup")
async def volunteer_signup(
    vol: VolunteerCreate, response: Response, db: Session = Depends(get_db)
):
    vol.password = hash_password(vol.password)

    volunteer_obj = create_volunteer(db, vol)
    sign_JWT_volunteer(volunteer_obj.id, response)
    return {
        "message": f"Volunteer {volunteer_obj.first_name} {volunteer_obj.last_name} with id {volunteer_obj.id} has been created!"
    }


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

    sign_JWT_volunteer(found_volunteer.id, response)
    return {
        "message": f"Volunteer {found_volunteer.first_name} {found_volunteer.last_name} has been logged in!"
    }


@router.post("/org/signup")
async def admin_signup(
    vol: AdminCreate, response: Response, db: Session = Depends(get_db)
):
    vol.password = hash_password(vol.password)
    admin_obj = create_org_admin(db, vol)
    sign_JWT_admin(admin_obj.id, response)
    return {
        "message": f"Admin {admin_obj.first_name} {admin_obj.last_name} with id {admin_obj.id} has been created!"
    }


@router.post("/org/login")
async def admin_login(
    login_data: LoginData, response: Response, db: Session = Depends(get_db)
):
    found_admin = get_admin_login(db, login_data.email)

    if found_admin is None:
        raise HTTPException(401, "User or password incorrect!")

    if not verify_password(login_data.password, found_admin.password):
        raise HTTPException(401, "User or password incorrect!")

    sign_JWT_admin(found_admin.id, response)
    return {
        "message": f"Admin {found_admin.first_name} {found_admin.last_name} has been logged in!"
    }


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
