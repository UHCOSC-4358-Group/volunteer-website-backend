from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from enum import Enum
from datetime import datetime, time, date

# === Location Models ===


class Location(BaseModel):
    """Base location model with all address components."""

    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=2, max_length=50)
    zip_code: str = Field(min_length=5, max_length=20)
    country: str = Field(min_length=2, max_length=100)


class EventUrgency(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class NotificationType(str, Enum):
    EVENT_ASSIGNMENT = "event_assignment"
    EVENT_REMINDER = "event_reminder"
    SKILL_MATCH = "skill_match"
    SYSTEM_UPDATE = "system_update"


class DayOfWeek(int, Enum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


# === Update Models ===


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location: Location | None = None  # Changed from str
    needed_skills: list[str] | None = None
    urgency: EventUrgency | None = None
    capacity: int | None = None
    day: date | None = None
    start_time: time | None = None
    end_time: time | None = None


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=10, max_length=800)
    location: Location | None = None


class OrgUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=10, max_length=800)
    location: Location | None = None


class Notification(BaseModel):
    id: int
    type: NotificationType
    text: str = Field(min_length=5, max_length=200)
    time: datetime


# This one is for creating events, so POST /:orgId/events
class EventCreate(BaseModel):
    name: str = Field(min_length=5, max_length=100)
    description: str = Field(min_length=10, max_length=800)
    location: Location | None = None
    needed_skills: list[str]
    urgency: EventUrgency
    capacity: int
    day: date
    start_time: time
    end_time: time
    org_id: int

    @field_validator("capacity")
    def capacity_positive(cls, v):
        if v <= 0:
            raise ValueError("Capacity must be positive")
        return v

    @model_validator(mode="after")
    def time_nonneg(self):
        if self.start_time >= self.end_time:
            raise ValueError("Time of Event must not be negative")
        return self


# This is for creating admins,
# usually done before they assign themselves to an org or create one
# ex. POST /admin/signup
class AdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=800)
    date_of_birth: date

    @field_validator("date_of_birth")
    def validate_over_18(cls, v: date):
        today = datetime.now().date()
        ago = date(today.year - 18, today.month, today.day)

        if v > ago:
            raise ValueError("User is not 18 years or older!")
        return v


class AvailableTime(BaseModel):
    day: DayOfWeek = Field(description="Day of the week (1-7)")
    start: time = Field(description="Start time (HH:MM)")
    end: time = Field(description="End time (HH:MM)")

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.start >= self.end:
            raise ValueError("start must be earlier than end")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"day": DayOfWeek.MONDAY, "start": "09:00", "end": "12:00"},
                {"day": DayOfWeek.WEDNESDAY, "start": "14:30", "end": "17:00"},
            ]
        }
    }


# For creating Volunteers
# ex. POST /vol/signup
class VolunteerCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=20)
    first_name: str = Field(min_length=1, max_length=40)
    last_name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=800)
    date_of_birth: date
    location: Location | None = None
    skills: list[str]
    available_times: list[AvailableTime] = Field(
        description="Weekly availability slots",
        json_schema_extra={
            "example": [
                {"day": DayOfWeek.MONDAY, "start": "09:00", "end": "12:00"},
                {"day": DayOfWeek.FRIDAY, "start": "13:00", "end": "16:30"},
            ]
        },
    )

    @field_validator("date_of_birth")
    def validate_over_18(cls, v: date):
        today = datetime.now().date()
        ago = date(today.year - 18, today.month, today.day)

        if v > ago:
            raise ValueError("User is not 18 years or older!")
        return v

    @model_validator(mode="after")
    def validate_non_overlapping(self):
        from collections import defaultdict

        by_day: dict[DayOfWeek, list[tuple[time, time]]] = defaultdict(list)
        for slot in self.available_times or []:
            by_day[slot.day].append((slot.start, slot.end))

        for day, slots in by_day.items():
            slots.sort(key=lambda s: s[0])
            last_end = None
            last_start = None
            for start, end in slots:
                if last_end is not None and start <= last_end:
                    raise ValueError(
                        f"Overlapping availability on {day.name}: {last_start}-{last_end} overlaps {start}-{end}"
                    )
                last_start, last_end = start, end

        return self
