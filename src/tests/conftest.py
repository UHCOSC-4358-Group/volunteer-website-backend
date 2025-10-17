# tests/conftest.py
"""
This file contains pytest fixtures that prepare a test environment for all backend unit tests.
It sets up a small FastAPI app, test client, and monkeypatches authentication functions.
That way, tests can run without needing a real JWT or database.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import your backend routers directly from the code under test
from src.routers import auth as auth_router_mod
from src.routers import event as event_router_mod


@pytest.fixture(autouse=True)
def patch_auth(monkeypatch):
    """
    This fixture automatically runs before every test.
    It overrides (monkeypatches) authentication and role functions,
    so tests can simulate 'admin' and 'volunteer' users easily
    without needing real tokens or password hashing.
    """

    class UserTokenInfo:
        def __init__(self, user_id: str, role: str):
            self.user_id = user_id
            self.role = role

    # Simple helper functions to identify user roles
    def is_admin(user_info):
        return getattr(user_info, "role", "") == "admin"

    def is_volunteer(user_info):
        return getattr(user_info, "role", "") == "volunteer"

    # Default user used for routes that require authentication
    def _get_current_user_admin():
        return UserTokenInfo(user_id="admin-1", role="admin")

    # Apply monkeypatch to override the real security functions
    for mod in (auth_router_mod, event_router_mod):
        monkeypatch.setattr(mod, "is_admin", is_admin, raising=False)
        monkeypatch.setattr(mod, "is_volunteer", is_volunteer, raising=False)
        monkeypatch.setattr(mod, "get_current_user", lambda: _get_current_user_admin(), raising=False)

    # If verify_password exists, simplify it for testing
    if hasattr(auth_router_mod, "verify_password"):
        monkeypatch.setattr(auth_router_mod, "verify_password", lambda p, s: p == s, raising=False)

    yield  # Let tests run with this setup


@pytest.fixture
def app():
    """
    Creates a lightweight FastAPI app for testing.
    Only mounts the two main routers (auth and event).
    """
    app = FastAPI(title="test-app")
    app.include_router(auth_router_mod.router)
    app.include_router(event_router_mod.router)
    return app


@pytest.fixture
def client(app):
    """
    Creates a TestClient that allows sending fake HTTP requests
    to the app during unit tests.
    """
    return TestClient(app)


@pytest.fixture
def as_admin(monkeypatch):
    """Simulates an authenticated admin user."""
    class U:
        user_id = "admin-1"
        role = "admin"
    monkeypatch.setattr(event_router_mod, "get_current_user", lambda: U(), raising=False)
    monkeypatch.setattr(auth_router_mod, "get_current_user", lambda: U(), raising=False)
    return U()


@pytest.fixture
def as_volunteer(monkeypatch):
    """Simulates an authenticated volunteer user."""
    class U:
        user_id = "vol-1"
        role = "volunteer"
    monkeypatch.setattr(event_router_mod, "get_current_user", lambda: U(), raising=False)
    monkeypatch.setattr(auth_router_mod, "get_current_user", lambda: U(), raising=False)
    return U()
