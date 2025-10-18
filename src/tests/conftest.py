# tests/conftest.py
"""
Shared pytest fixtures for FastAPI app tests.
- Keeps source unchanged; mocks DB and auth in tests only.
- Applies dependency_overrides on the FastAPI app so role checks work per-test.
"""
import os
import sys
import importlib
import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from types import SimpleNamespace

# Ensure project root on path so 'src.*' imports work when running from repo root
_THIS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Import the code under test
from src.routers import auth as auth_router_mod
from src.routers import event as event_router_mod
from src.dependencies.database.config import get_db as real_get_db


@pytest.fixture(autouse=True)
def patch_auth(monkeypatch):
    """
    Automatically stub auth and persistence helpers:
    - verify_password => plain equality
    - JWT signing => passthrough
    - No real DB access required
    - Optional: stub CRUD used by auth router (if present)
    """

    # 1) Password check is equality for tests
    if hasattr(auth_router_mod, "verify_password"):
        monkeypatch.setattr(
            auth_router_mod,
            "verify_password",
            lambda plain, hashed: plain == hashed,
            raising=False,
        )

    # 2) JWT signers: just return the response payload to keep tests simple
    monkeypatch.setattr(
        auth_router_mod, "sign_JWT_volunteer", lambda _uid, resp: resp, raising=False
    )
    monkeypatch.setattr(
        auth_router_mod, "sign_JWT_admin", lambda _uid, resp: resp, raising=False
    )

    # 3) Light-weight in-memory store for optional CRUD stubs
    _ids = {"vol": 1000, "admin": 2000}
    _store = {"vol": {}, "admin": {}}

    def _fake_get_db():
        # No DB needed for tests
        yield None

    def _mk(data: dict):
        # Build a simple object (avoid duplicate kwargs like id)
        return SimpleNamespace(**data)

    def _append_if_dummy_list_exists(kind: str, obj):
        # Keep auth module's dummy lists in sync if present (used by tests)
        if kind == "vol" and hasattr(auth_router_mod, "VOLUNTEER_DUMMY_DATA"):
            auth_router_mod.VOLUNTEER_DUMMY_DATA.append(obj)
        if kind == "admin" and hasattr(auth_router_mod, "ADMIN_DUMMY_DATA"):
            auth_router_mod.ADMIN_DUMMY_DATA.append(obj)

    def create_volunteer(_db, new_vol):
        _ids["vol"] += 1
        vid = _ids["vol"]
        data = {
            "id": vid,
            "email": getattr(new_vol, "email", None),
            "password": getattr(new_vol, "password", None),
            "first_name": getattr(new_vol, "first_name", None),
            "last_name": getattr(new_vol, "last_name", None),
            "description": getattr(new_vol, "description", None),
            "image_url": getattr(new_vol, "image_url", None),
            "location": getattr(new_vol, "location", None),
        }
        _store["vol"][vid] = data
        obj = _mk(data)
        _append_if_dummy_list_exists("vol", obj)
        return obj

    def create_org_admin(_db, new_admin):
        _ids["admin"] += 1
        aid = _ids["admin"]
        data = {
            "id": aid,
            "org_id": getattr(new_admin, "org_id", None),
            "email": getattr(new_admin, "email", None),
            "password": getattr(new_admin, "password", None),
            "first_name": getattr(new_admin, "first_name", None),
            "last_name": getattr(new_admin, "last_name", None),
            "description": getattr(new_admin, "description", None),
            "image_url": getattr(new_admin, "image_url", None),
        }
        _store["admin"][aid] = data
        obj = _mk(data)
        _append_if_dummy_list_exists("admin", obj)
        return obj

    def get_volunteer_login(_db, email: str):
        # Search in-memory store first
        for v in _store["vol"].values():
            if v.get("email") == email:
                return _mk(v)
        # Fallback to dummy data list if present
        if hasattr(auth_router_mod, "VOLUNTEER_DUMMY_DATA"):
            for v in auth_router_mod.VOLUNTEER_DUMMY_DATA:
                ve = getattr(v, "email", None)
                if ve == email:
                    # Return a simple namespace with expected fields
                    return SimpleNamespace(
                        id=getattr(v, "id", None),
                        email=getattr(v, "email", None),
                        password=getattr(v, "password", None),
                        first_name=getattr(v, "first_name", None),
                        last_name=getattr(v, "last_name", None),
                    )
        return None

    def get_admin_login(_db, email: str):
        for a in _store["admin"].values():
            if a.get("email") == email:
                return _mk(a)
        if hasattr(auth_router_mod, "ADMIN_DUMMY_DATA"):
            for a in auth_router_mod.ADMIN_DUMMY_DATA:
                ae = getattr(a, "email", None)
                if ae == email:
                    return SimpleNamespace(
                        id=getattr(a, "id", None),
                        email=getattr(a, "email", None),
                        password=getattr(a, "password", None),
                        first_name=getattr(a, "first_name", None),
                        last_name=getattr(a, "last_name", None),
                    )
        return None

    # Patch only if the auth module actually exposes these names
    monkeypatch.setattr(auth_router_mod, "get_db", _fake_get_db, raising=False)
    if hasattr(auth_router_mod, "create_volunteer"):
        monkeypatch.setattr(
            auth_router_mod, "create_volunteer", create_volunteer, raising=False
        )
    if hasattr(auth_router_mod, "create_org_admin"):
        monkeypatch.setattr(
            auth_router_mod, "create_org_admin", create_org_admin, raising=False
        )
    if hasattr(auth_router_mod, "get_volunteer_login"):
        monkeypatch.setattr(
            auth_router_mod, "get_volunteer_login", get_volunteer_login, raising=False
        )
    if hasattr(auth_router_mod, "get_admin_login"):
        monkeypatch.setattr(
            auth_router_mod, "get_admin_login", get_admin_login, raising=False
        )

    yield


# Optionally collect common auth dependency callables so we can override them on the app
def _import_optional(modpath):
    try:
        return importlib.import_module(modpath)
    except Exception:
        return None


_deps_modules = list(
    filter(
        None,
        [
            _import_optional("src.dependencies.auth"),
            _import_optional("src.dependencies.security"),
            _import_optional("src.dependencies.authentication"),
        ],
    )
)

_AUTH_DEP_NAMES = [
    "get_current_user",
    "get_current_admin",
    "get_current_volunteer",
    "require_admin",
    "require_volunteer",
    "admin_required",
    "volunteer_required",
]


def _collect_auth_deps():
    """Collect dependency callables that routes might be using via Depends()."""
    funcs = set()
    for mod in [auth_router_mod, event_router_mod] + _deps_modules:
        if not mod:
            continue
        for name in _AUTH_DEP_NAMES:
            if hasattr(mod, name):
                func = getattr(mod, name)
                if callable(func):
                    funcs.add(func)
    return funcs


def _unauth_dep():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )


def _require_role(user, required_role: str):
    def _dep():
        role = getattr(user, "role", None)
        if role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
        return user

    return _dep


def _set_unauth_overrides(app: FastAPI):
    """Default state: not authenticated -> protected routes return 401."""
    for dep in _collect_auth_deps():
        name = getattr(dep, "__name__", "")
        if "get_current" in name:
            app.dependency_overrides[dep] = _unauth_dep
        elif "admin" in name or "volunteer" in name or "require" in name:
            app.dependency_overrides[dep] = _unauth_dep


def _set_auth_overrides(app: FastAPI, user):
    """
    Override all captured auth dependencies on the FastAPI app so role checks work in tests.
    """
    for dep in _collect_auth_deps():
        name = getattr(dep, "__name__", "")
        if "admin" in name and "volunteer" not in name:
            app.dependency_overrides[dep] = _require_role(user, "admin")
        elif "volunteer" in name:
            app.dependency_overrides[dep] = _require_role(user, "volunteer")
        elif "get_current" in name:
            # Generic "get_current_user"
            app.dependency_overrides[dep] = lambda u=user: u


@pytest.fixture
def app():
    """
    Creates a lightweight FastAPI app for testing and overrides DB/auth deps.
    """
    app = FastAPI(title="test-app")
    app.include_router(auth_router_mod.router)
    app.include_router(event_router_mod.router)

    # Override DB dependency so tests don't require lifespan/SessionLocal
    def _fake_get_db():
        yield None

    app.dependency_overrides[real_get_db] = _fake_get_db

    # Default to unauthenticated; per-test fixtures will switch roles
    _set_unauth_overrides(app)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def as_admin(app, monkeypatch):
    """Simulate an authenticated admin user for the current test."""
    user = SimpleNamespace(id=1, user_id=1, role="admin")
    _set_auth_overrides(app, user)
    # Optional: module-level fallbacks (harmless but helps direct calls)
    monkeypatch.setattr(
        event_router_mod, "get_current_user", lambda: user, raising=False
    )
    monkeypatch.setattr(
        auth_router_mod, "get_current_user", lambda: user, raising=False
    )
    return user


@pytest.fixture
def as_volunteer(app, monkeypatch):
    """Simulate an authenticated volunteer user for the current test."""
    user = SimpleNamespace(id=1, user_id=1, role="volunteer")
    _set_auth_overrides(app, user)
    monkeypatch.setattr(
        event_router_mod, "get_current_user", lambda: user, raising=False
    )
    monkeypatch.setattr(
        auth_router_mod, "get_current_user", lambda: user, raising=False
    )
    return user
