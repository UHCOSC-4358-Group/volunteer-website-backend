from fastapi import APIRouter, Response, Depends, HTTPException, responses
from pydantic import BaseModel, EmailStr
from ..models.models import VolunteerCreate, Volunteer, AdminCreate, OrgAdmin
from ..dependencies.auth import (
    hash_password,
    verify_password,
    sign_JWT_volunteer,
    sign_JWT_admin,
    get_current_user,
)
from uuid import uuid4

# Sample volunteer data for testing
VOLUNTEER_DUMMY_DATA: list[Volunteer] = [
    Volunteer(
        id="550e8400-e29b-41d4-a716-446655440001",
        email="sarah.johnson@email.com",
        password=hash_password("testpass123"),
        first_name="Sarah",
        last_name="Johnson",
        description="Passionate about community service with 3 years of experience in disaster relief and food distribution programs.",
        image_url="https://example.com/profiles/sarah.jpg",
        location="Austin, TX",
        skills=["First Aid", "Event Planning", "Spanish Translation", "Food Service"],
    ),
    Volunteer(
        id="550e8400-e29b-41d4-a716-446655440002",
        email="mike.chen@email.com",
        password=hash_password("volunteer2024"),
        first_name="Mike",
        last_name="Chen",
        description="Software engineer looking to give back to the community through tech education and environmental conservation efforts.",
        image_url="https://example.com/profiles/mike.jpg",
        location="Seattle, WA",
        skills=[
            "Programming",
            "Teaching",
            "Environmental Cleanup",
            "Data Analysis",
            "Photography",
        ],
    ),
    Volunteer(
        id="550e8400-e29b-41d4-a716-446655440003",
        email="maria.rodriguez@email.com",
        password=hash_password("helpingHands99"),
        first_name="Maria",
        last_name="Rodriguez",
        description="Retired nurse with decades of healthcare experience, eager to support medical outreach and senior care programs.",
        image_url="https://example.com/profiles/maria.jpg",
        location="Phoenix, AZ",
        skills=[
            "Medical Care",
            "Elder Care",
            "Bilingual Communication",
            "Crisis Management",
        ],
    ),
]

ADMIN_DUMMY_DATA: list[OrgAdmin] = []

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
    VOLUNTEER_DUMMY_DATA.append(new_volunteer)
    sign_JWT_volunteer(new_volunteer.id, response)
    return {
        "message": f"Volunteer {new_volunteer.first_name} {new_volunteer.last_name} has been created!"
    }


class LoginData(BaseModel):
    email: EmailStr
    password: str


@router.post("/vol/login")
async def volunteer_login(login_data: LoginData, response: Response):
    found_volunteers = [
        vol for vol in VOLUNTEER_DUMMY_DATA if login_data.email == vol.email
    ]
    if len(found_volunteers) == 0:
        raise HTTPException(400, "User or password incorrect!")
    # just grab the first one for now
    found_volunteer = found_volunteers[0]

    if not verify_password(login_data.password, found_volunteer.password):
        raise HTTPException(400, "User or password incorrect!")

    sign_JWT_volunteer(found_volunteer.id, response)
    return {
        "message": f"Volunteer {found_volunteer.first_name} {found_volunteer.last_name} has been logged in!"
    }


@router.post("/org/signup")
async def admin_signup(user: AdminCreate, response: Response):
    id = str(uuid4())
    password = hash_password(user.password)
    new_admin = OrgAdmin(
        id=id,
        password=password,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        description=user.description,
        image_url=user.image_url,
    )
    ADMIN_DUMMY_DATA.append(new_admin)
    sign_JWT_admin(new_admin.id, response)
    return {
        "message": f"Admin {new_admin.first_name} {new_admin.last_name} has been created!"
    }


@router.post("/org/login")
async def admin_login(login_data: LoginData, response: Response):
    found_admins = [
        admin for admin in ADMIN_DUMMY_DATA if login_data.email == admin.email
    ]
    if len(found_admins) == 0:
        raise HTTPException(400, "User or password incorrect!")
    # just grab the first one for now
    found_admin = found_admins[0]

    if not verify_password(login_data.password, found_admin.password):
        raise HTTPException(400, "User or password incorrect!")

    sign_JWT_admin(found_admin.id, response)
    return {
        "message": f"Admin {found_admin.first_name} {found_admin.last_name} has been logged in!"
    }


@router.get("/vol")
async def get_volunteer(user_id=Depends(get_current_user)):
    volunteer: Volunteer | None = None
    for vol in VOLUNTEER_DUMMY_DATA:
        if vol.id == user_id:
            volunteer = vol

    if volunteer is None:
        raise HTTPException(status_code=400, detail="User not found!")

    return volunteer
