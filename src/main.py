from fastapi import FastAPI, status
import json
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .models.models import VolunteerCreate

app = FastAPI(
    title="Volunteer Website API",
    description="Backend API for volunteer website",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FIXME: CHANGE FOR PRODUCTION LATER
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DUMMY_DATA: list[VolunteerCreate] = []


@app.post("/vol/signup")
async def volunteer_signup(user: VolunteerCreate):
    DUMMY_DATA.append(user)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": f"Volunteer {user.first_name} {user.last_name} has been created"
        },
    )


@app.get("/vol")
async def all_volunteers():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=[Volunteer.model_dump_json(indent=4) for Volunteer in DUMMY_DATA],
    )


@app.get("/")
async def root():
    return {"message": "Welcome to Volunteer Website API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
