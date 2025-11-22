import itertools
import pytest
from datetime import date, datetime, time
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Any, Protocol
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
            "location_id": None,
            "date_of_birth": date(2002, 11, 11),
        }

    def _admin_defaults(n: int) -> dict[str, Any]:
        return {
            "email": f"admin{n}@example.com",
            "password": "x",
            "first_name": f"First{n}",
            "last_name": f"Last{n}",
            "description": "",
            "image_url": "",
            "date_of_birth": date(2002, 11, 11),
        }

    def _organization_defaults(n: int) -> dict[str, Any]:
        return {
            "name": f"Org {n}",
            "location_id": None,
            "description": "",
            "image_url": "",
        }

    def _event_defaults(n: int) -> dict[str, Any]:
        return {
            "name": f"Event {n}",
            "description": "desc",
            "location_id": None,
            "urgency": dbmodels.EventUrgency.LOW,
            "capacity": 5,
            "assigned": 0,
            "day": date(2025, 12, 4),
            "start_time": time(4, 30, 0),
            "end_time": time(7, 30, 0),
        }

    class F:
        def volunteer(self, **overrides: Any) -> dbmodels.Volunteer:
            n = next(counter)
            data = {**_volunteer_defaults(n), **overrides}

            # Create location if not provided
            if data.get("location_id") is None:
                location = dbmodels.Location(
                    address="1100 Congress Ave.",
                    city="Austin",
                    state="Texas",
                    country="USA",
                    zip_code="78701",
                    latitude=30.276513,
                    longitude=-97.739758,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db_session.add(location)
                db_session.flush()
                data["location_id"] = location.id
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

            # Create location if not provided
            if data.get("location_id") is None:
                location = dbmodels.Location(
                    address="1100 Congress Ave.",
                    city="Austin",
                    state="Texas",
                    country="USA",
                    zip_code="78701",
                    latitude=30.276513,
                    longitude=-97.739758,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db_session.add(location)
                db_session.flush()
                data["location_id"] = location.id
            org = dbmodels.Organization(**data)
            db_session.add(org)
            db_session.commit()
            return org

        def event(self, **overrides: Any) -> dbmodels.Event:
            n = next(counter)
            data = {**_event_defaults(n), **overrides}

            # Create location if not provided
            if data.get("location_id") is None:
                location = dbmodels.Location(
                    address="1100 Congress Ave.",
                    city="Austin",
                    state="Texas",
                    country="USA",
                    zip_code="78701",
                    latitude=30.276513,
                    longitude=-97.739758,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db_session.add(location)
                db_session.flush()
                data["location_id"] = location.id

            org_obj = data.pop("org", None)
            if org_obj is not None:
                data["org_id"] = org_obj.id

            if data.get("org_id") is None:
                org = self.organization()
                data["org_id"] = org.id

            ev = dbmodels.Event(**data)
            db_session.add(ev)
            db_session.commit()
            return ev

    return F()
