import itertools
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Any, Protocol, Optional
from src.models import dbmodels


class Factories(Protocol):
    def volunteer(self, **overrides: Any) -> dbmodels.Volunteer: ...
    def admin(self, **overrides: Any) -> dbmodels.OrgAdmin: ...
    def organization(self, **overrides: Any) -> dbmodels.Organization: ...
    def event(self, **overrides: Any) -> dbmodels.Event: ...


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


with engine.begin() as conn:
    dbmodels.Base.metadata.create_all(bind=conn)


SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)


@pytest.fixture
def db_session():
    connection = engine.connect()
    outer = connection.begin()
    session = SessionLocal(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if not connection.in_nested_transaction():
            connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def factories(db_session: Session) -> Factories:
    counter = itertools.count(1)

    def _volunteer_defaults(n: int) -> dict[str, Any]:
        return {
            "email": f"user{n}@example.com",
            "password": "x",
            "first_name": f"First{n}",
            "last_name": f"Last{n}",
            "description": "",
            "image_url": "",
            "location": "Houston",
        }

    def _admin_defaults(n: int) -> dict[str, Any]:
        return {
            "email": f"admin{n}@example.com",
            "password": "x",
            "first_name": f"First{n}",
            "last_name": f"Last{n}",
            "description": "",
            "image_url": "",
        }

    def _organization_defaults(n: int) -> dict[str, Any]:
        return {
            "name": f"Org {n}",
            "location": "Houston",
            "description": "",
            "image_url": "",
        }

    def _event_defaults(n: int) -> dict[str, Any]:
        return {
            "name": f"Event {n}",
            "description": "desc",
            "location": "Houston",
            "urgency": dbmodels.EventUrgency.LOW,
            "capacity": 5,
            # org_id will be filled automatically if not provided
        }

    class F:
        def volunteer(self, **overrides: Any) -> dbmodels.Volunteer:
            n = next(counter)
            data = {**_volunteer_defaults(n), **overrides}
            v = dbmodels.Volunteer(**data)
            db_session.add(v)
            db_session.commit()
            return v

        def admin(self, **overrides: Any) -> dbmodels.OrgAdmin:
            n = next(counter)
            data = {**_admin_defaults(n), **overrides}
            a = dbmodels.OrgAdmin(**data)
            db_session.add(a)
            db_session.commit()
            return a

        def organization(self, **overrides: Any) -> dbmodels.Organization:
            n = next(counter)
            data = {**_organization_defaults(n), **overrides}
            org = dbmodels.Organization(**data)
            db_session.add(org)
            db_session.commit()
            return org

        def event(self, **overrides: Any) -> dbmodels.Event:
            n = next(counter)
            data = {**_event_defaults(n), **overrides}

            # Allow passing an Organization instance directly
            org_obj = data.pop("org", None)
            if org_obj is not None:
                data["org_id"] = org_obj.id

            # If no org_id provided, auto-create an organization
            if "org_id" not in data or data["org_id"] is None:
                org = self.organization()
                data["org_id"] = org.id

            ev = dbmodels.Event(**data)
            db_session.add(ev)
            db_session.commit()
            return ev

    return F()
