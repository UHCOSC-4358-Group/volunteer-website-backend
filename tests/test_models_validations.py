# tests/test_models_validation.py
"""
Tests for Pydantic data model validation.
Ensures fields follow required formats, types, and value limits.
"""

import pytest
from pydantic import ValidationError

# Import model definitions
from src.models.models import EventCreate, AdminCreate, VolunteerCreate


def test_event_create_capacity_must_be_positive():
    """
    The 'capacity' field for events must be positive.
    This ensures invalid data is caught before saving.
    """
    with pytest.raises(ValidationError):
        EventCreate(
            name="Valid Name",
            description="Long enough description here",
            location="Here",
            required_skills=["A"],
            urgency="Low",
            capacity=0,  # invalid
        )


def test_admin_create_email_validation():
    """
    The AdminCreate model must reject invalid emails.
    Pydantic's EmailStr enforces this automatically.
    """
    with pytest.raises(ValidationError):
        AdminCreate(
            email="not-an-email",
            password="Password12",
            first_name="A",
            last_name="B",
            description="A valid description long enough",
            image_url="https://img",
        )


def test_volunteer_create_fields_valid():
    """
    Ensure the VolunteerCreate model accepts valid input.
    This confirms all required fields and data types work correctly.
    """
    VolunteerCreate(
        email="vol@example.com",
        password="Password12",
        first_name="A",
        last_name="B",
        description="A valid description long enough",
        image_url="https://img",
        location="TX",
        skills=["First Aid", "Spanish"],
    )
