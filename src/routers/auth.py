from fastapi import APIRouter, Response, Depends, HTTPException
from pydantic import EmailStr
from ..models.models import VolunteerCreate, Volunteer
from ..dependencies.auth import (
    hash_password,
    verify_password,
    sign_JWT,
    get_current_user,
)
from uuid import uuid4


DUMMY_DATA: list[Volunteer] = []

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/vol/signup")
async def volunteer_signup(user: VolunteerCreate, response: Response):
    id = str(uuid4())
    password = hash_password(user.password)
    new_volunteer = Volunteer(
        id=id,
        password=password,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        description=user.description,
        image_url=user.image_url,
        location=user.location,
        skills=user.skills,
    )
    DUMMY_DATA.append(new_volunteer)
    tokenized_response = sign_JWT(new_volunteer.id, response)
    return tokenized_response


@router.post("/vol/login")
async def volunteer_login(email: EmailStr, password: str):
    found_volunteers = [vol for vol in DUMMY_DATA if email == vol.email]
    if len(found_volunteers) == 0:
        raise HTTPException(400, "User or password incorrect!")
    # just grab the first one for now
    found_volunteer = found_volunteers[0]

    if not verify_password(password, found_volunteer.password):
        raise HTTPException(400, "User or password incorrect!")

    tokenized_response = sign_JWT(found_volunteer.id, Response())
    return tokenized_response


@router.get("/vol")
async def get_volunteer(user_id=Depends(get_current_user)):
    volunteer: Volunteer | None = None
    for vol in DUMMY_DATA:
        if vol.id == user_id:
            volunteer = vol

    if volunteer is None:
        raise HTTPException(status_code=400, detail="User not found!")

    return volunteer
