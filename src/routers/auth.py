from fastapi import APIRouter, Response, Depends, HTTPException, responses
from pydantic import BaseModel, EmailStr
from ..models.models import VolunteerCreate, Volunteer, AdminCreate, OrgAdmin
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

ADMIN_DUMMY_DATA: list[OrgAdmin] = [
    OrgAdmin(
        id="admin-550e8400-e29b-41d4-a716-446655440001",
        org_id="org-550e8400-e29b-41d4-a716-446655440001",
        email="jennifer.smith@redcross.org",
        password=hash_password("adminpass123"),
        first_name="Jennifer",
        last_name="Smith",
        description="Regional coordinator with 8 years of experience managing disaster relief operations and volunteer programs across Texas.",
        image_url="https://example.com/profiles/jennifer.jpg",
    ),
    OrgAdmin(
        id="admin-550e8400-e29b-41d4-a716-446655440002",
        org_id="org-550e8400-e29b-41d4-a716-446655440002",
        email="david.kumar@foodbank.org",
        password=hash_password("foodbank2024"),
        first_name="David",
        last_name="Kumar",
        description="Operations manager specializing in food distribution logistics and community outreach programs for underserved populations.",
        image_url="https://example.com/profiles/david.jpg",
    ),
    OrgAdmin(
        id="admin-550e8400-e29b-41d4-a716-446655440003",
        org_id="org-550e8400-e29b-41d4-a716-446655440003",
        email="lisa.torres@codeforchange.org",
        password=hash_password("techvolunteer99"),
        first_name="Lisa",
        last_name="Torres",
        description="Tech nonprofit director focused on digital literacy education and bridging the technology gap in underserved communities.",
        image_url="https://example.com/profiles/lisa.jpg",
    ),
]

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/vol/signup")
async def volunteer_signup(
    user: VolunteerCreate, response: Response, db: Session = Depends(get_db)
):
    user.password = hash_password(user.password)

    volunteer_obj = create_volunteer(db, user)
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
    user: AdminCreate, response: Response, db: Session = Depends(get_db)
):
    user.password = hash_password(user.password)
    admin_obj = create_org_admin(db, user)
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

    # Shouldn't happen...
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
