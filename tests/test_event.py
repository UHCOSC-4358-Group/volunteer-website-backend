# tests/test_event.py
"""
Tests for event management routes.
Includes fetching events, admin-only creation, updates, and deletions.
"""

import copy
import pytest
from src.routers import event as event_mod


def test_get_event_by_id_success(client):
    """Verify that fetching an existing event by ID returns 200."""
    if not getattr(event_mod, "EVENT_DUMMY_DATA", None):
        pytest.skip("No EVENT_DUMMY_DATA available")
    eid = event_mod.EVENT_DUMMY_DATA[0].id
    r = client.get(f"/events/{eid}")
    assert r.status_code == 200
    assert r.json()["id"] == eid


def test_get_event_by_id_not_found(client):
    """Ensure that a non-existing event returns 404."""
    r = client.get("/events/evt-does-not-exist")
    assert r.status_code == 404


def test_admin_create_event_success(client, as_admin):
    """
    Test that an admin can successfully create a new event.
    Checks that EVENT_DUMMY_DATA list grows by 1.
    """
    before = len(getattr(event_mod, "EVENT_DUMMY_DATA", []))
    payload = {
        "name": "Neighborhood Clean-up",
        "description": "Pick up trash at the park.",
        "location": "Memorial Park",
        "required_skills": ["Environmental Cleanup"],
        "urgency": "Low",
        "capacity": 10
    }
    r = client.post("/events/create/1", json=payload)
    assert r.status_code in (200, 201)
    after = len(getattr(event_mod, "EVENT_DUMMY_DATA", []))
    assert after == before + 1


def test_admin_update_event_capacity_validation(client, as_admin):
    """
    Ensure that the update helper enforces that assigned <= capacity.
    If not, it should raise a ValueError.
    """
    helper = getattr(event_mod, "update_event_helper", None)
    if helper is None:
        pytest.skip("update_event_helper not found")

    evt = copy.deepcopy(event_mod.EVENT_DUMMY_DATA[0])
    evt.assigned = 5  # current volunteers assigned

    class Update:
        name=None; description=None; location=None; required_skills=None; urgency=None; assigned=None; capacity=3

    with pytest.raises((ValueError, AssertionError)):
        helper(evt, Update)


def test_delete_event_requires_admin(client):
    """Verify that only admins can delete events."""
    class V:
        user_id = "v1"
        role = "volunteer"
    event_mod.get_current_user = lambda: V()

    if not getattr(event_mod, "EVENT_DUMMY_DATA", None):
        pytest.skip("No EVENT_DUMMY_DATA available")

    target_id = event_mod.EVENT_DUMMY_DATA[0].id
    r = client.delete(f"/events/{target_id}")
    assert r.status_code in (401, 403)


def test_delete_event_success(client, as_admin):
    """Confirm that admins can delete events successfully."""
    payload = {
        "name": "Temp Event",
        "description": "To be deleted",
        "location": "Somewhere",
        "required_skills": [],
        "urgency": "Medium",
        "capacity": 2
    }
    r = client.post("/events/create/1", json=payload)
    assert r.status_code in (200, 201)

    new_id = event_mod.EVENT_DUMMY_DATA[-1].id
