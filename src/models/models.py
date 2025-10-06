from pydantic import BaseModel, Field, field_validator, EmailStr
from enum import Enum
from datetime import datetime


# TODO: CHANGE INTO SQLALCHEMY MODELS
# Our Pydantic models will be in the same


class UrgencyLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class NotificationType(str, Enum):
    EVENT_ASSIGNMENT = "event_assignment"
    EVENT_REMINDER = "event_reminder"
    SKILL_MATCH = "skill_match"
    SYSTEM_UPDATE = "system_update"


class Event(BaseModel):
    id: int
    name: str = Field(min_length=5, max_length=100)
    description: str = Field(min_length=10, max_length=800)
    location: str
    required_skills: list[str]
    urgency: UrgencyLevel
    assigned: int
    capacity: int
    created_by: int
    org_id: int


class Org(BaseModel):
    id: int
    name: str = Field(min_length=5, max_length=100)
    description: str = Field(min_length=10, max_length=800)
    image_url: str


class OrgAdmin(BaseModel):
    id: int
    org_id: int | None
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=800)
    image_url: str


class Volunteer(BaseModel):
    id: int
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=800)
    image_url: str
    location: str
    skills: list[str]


class Notification(BaseModel):
    id: int
    type: NotificationType
    text: str = Field(min_length=5, max_length=200)
    time: datetime


# This one is for creating events, so POST /:orgId/events
class EventCreate(BaseModel):
    name: str = Field(min_length=5, max_length=100)
    description: str = Field(min_length=10, max_length=800)
    location: str
    required_skills: list[str]
    urgency: UrgencyLevel
    capacity: int
    created_by: int
    org_id: int

    @field_validator("capacity")
    def capacity_positive(cls, v):
        if v <= 0:
            raise ValueError("Capacity must be positive")
        return v


# This is for creating admins,
# usually done before they assign themselves to an org or create one
# ex. POST /admin/signup
class AdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=800)
    image_url: str


# For creating Volunteers
# ex. POST /vol/signup
class VolunteerCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    location: str
    skills: list[str]
