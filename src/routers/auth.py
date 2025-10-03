from fastapi import APIRouter
from ..models.models import VolunteerCreate


DUMMY_DATA: list[VolunteerCreate] = []

router = APIRouter(prefix="/auth", tags=["users, auth, signup, login"])


@router.post("/vol/signup", status_code=201)
async def volunteer_signup(user: VolunteerCreate):
    DUMMY_DATA.append(user)
    return {
        "message": f"New volunteer {user.first_name} {user.last_name} has been created"
    }
