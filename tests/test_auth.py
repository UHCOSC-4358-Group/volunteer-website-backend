# tests/test_auth.py
"""
Tests for the authentication system.
Covers volunteer login, admin signup + login, and role-based route access.
"""

import copy
import pytest
from src.routers import auth as auth_mod


def test_volunteer_login_success(client, monkeypatch):
    """
    Test that a volunteer can log in successfully with the correct password.
    Temporarily overrides the volunteer's password to a known test value.
    """
    if hasattr(auth_mod, "VOLUNTEER_DUMMY_DATA") and auth_mod.VOLUNTEER_DUMMY_DATA:
        original = copy.deepcopy(auth_mod.VOLUNTEER_DUMMY_DATA[0])
        auth_mod.VOLUNTEER_DUMMY_DATA[0].password = "testpass123"
        email = auth_mod.VOLUNTEER_DUMMY_DATA[0].email

        try:
            r = client.post("/auth/vol/login", json={"email": email, "password": "testpass123"})
            assert r.status_code == 200
            assert "logged" in r.json().get("message", "").lower()
        finally:
            # restore original data after test
            auth_mod.VOLUNTEER_DUMMY_DATA[0] = original
    else:
        pytest.skip("No VOLUNTEER_DUMMY_DATA available")


def test_volunteer_login_bad_password(client):
    """Ensure a volunteer cannot log in with an incorrect password."""
    if hasattr(auth_mod, "VOLUNTEER_DUMMY_DATA") and auth_mod.VOLUNTEER_DUMMY_DATA:
        email = auth_mod.VOLUNTEER_DUMMY_DATA[0].email
        auth_mod.VOLUNTEER_DUMMY_DATA[0].password = "right"
        r = client.post("/auth/vol/login", json={"email": email, "password": "wrong"})
        assert r.status_code in (400, 401)
    else:
        pytest.skip("No VOLUNTEER_DUMMY_DATA available")


def test_admin_signup_and_login_flow(client):
    """
    Test that an admin can register (signup) and then log in successfully.
    Validates both endpoints and makes sure new accounts are added.
    """
    payload = {
        "email": "new.admin@example.com",
        "password": "AdminPass123",
        "first_name": "New",
        "last_name": "Admin",
        "description": "I run things.",
        "image_url": "https://example.com/a.png"
    }
    # Test admin signup endpoint
    r = client.post("/auth/org/signup", json=payload)
    assert r.status_code in (200, 201)

    # Modify stored password to match plain text for verify stub
    if hasattr(auth_mod, "ADMIN_DUMMY_DATA"):
        created = [a for a in auth_mod.ADMIN_DUMMY_DATA if a.email == payload["email"]]
        if created:
            created[0].password = payload["password"]

    # Test admin login endpoint
    r2 = client.post("/auth/org/login", json={"email": payload["email"], "password": payload["password"]})
    assert r2.status_code == 200


def test_get_volunteer_requires_volunteer_role(client, as_volunteer):
    """Ensure that the /auth/vol route works for volunteers."""
    r = client.get("/auth/vol")
    assert r.status_code == 200


def test_get_volunteer_rejects_admin(client, as_admin):
    """Ensure that admins are rejected from volunteer-only routes."""
    r = client.get("/auth/vol")
    assert r.status_code in (401, 403)
