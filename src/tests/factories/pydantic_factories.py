from __future__ import annotations

import itertools
from typing import Any, Callable, Dict, Generic, Type, TypeVar
from datetime import time, date

from pydantic import BaseModel
from src.models import pydanticmodels

T = TypeVar("T", bound=BaseModel)
_counter = itertools.count(1)


class ModelFactory(Generic[T]):
    """
    Generic factory for Pydantic models that provides:
    - build(**overrides) -> T instance
    - dict(**overrides) -> dict payload
    You pass a model class and a defaults() function that returns base fields.
    """

    def __init__(self, model: Type[T], defaults: Callable[[int], Dict[str, Any]]):
        self._model = model
        self._defaults = defaults

    def build(self, **overrides: Any) -> T:
        n = next(_counter)
        data = {**self._defaults(n), **overrides}
        return self._model(**data)

    def dict(self, **overrides: Any) -> Dict[str, Any]:
        return self.build(**overrides).model_dump(mode="json")


# Example: VolunteerCreate factory
def _volunteer_create_defaults(n: int) -> Dict[str, Any]:
    return {
        "email": f"user{n}@example.com",
        "password": "secret123!",
        "first_name": f"First{n}",
        "last_name": f"Last{n}",
        "description": "test_volunteer",
        "location": pydanticmodels.Location(
            address="1100 Congress Ave.",
            city="Austin",
            state="Texas",
            country="USA",
            zip_code="78701",
        ),
        "skills": ["x"],
        "available_times": [
            pydanticmodels.AvailableTime(
                day=pydanticmodels.DayOfWeek.MONDAY,
                start=time(12, 0, 0),
                end=time(17, 0, 0),
            ),
        ],
        "date_of_birth": date(2002, 2, 23),
    }


volunteer = ModelFactory[pydanticmodels.VolunteerCreate](
    pydanticmodels.VolunteerCreate,
    _volunteer_create_defaults,
)


def _event_create_defaults(n: int) -> Dict[str, Any]:
    return {
        "name": f"Event {n}",
        "description": f"Description {n}",
        "location": "Houston",
        "urgency": pydanticmodels.EventUrgency.LOW,
        "capacity": 5,
        "location": pydanticmodels.Location(
            address="1100 Congress Ave.",
            city="Austin",
            state="Texas",
            country="USA",
            zip_code="78701",
        ),
        "org_id": 1,
        "needed_skills": ["x"],
        "day": date(2025, 12, 4),
        "start_time": time(4, 30, 0),
        "end_time": time(7, 30, 0),
    }


event = ModelFactory[pydanticmodels.EventCreate](
    pydanticmodels.EventCreate,
    _event_create_defaults,
)


def _admin_create_defaults(n: int) -> Dict[str, Any]:
    return {
        "email": f"user{n}@example.com",
        "password": "secret123!",
        "first_name": f"First{n}",
        "last_name": f"Last{n}",
        "description": "test_admin",
        "date_of_birth": date(2002, 11, 1),
    }


admin = ModelFactory[pydanticmodels.AdminCreate](
    pydanticmodels.AdminCreate, _admin_create_defaults
)


def _org_create_defaults(n: int) -> Dict[str, Any]:
    return {
        "name": f"x{n}",
        "description": "test_organization",
        "location": pydanticmodels.Location(
            address="1100 Congress Ave.",
            city="Austin",
            state="Texas",
            country="USA",
            zip_code="78701",
        ),
    }


org = ModelFactory[pydanticmodels.OrgCreate](
    pydanticmodels.OrgCreate, _org_create_defaults
)
