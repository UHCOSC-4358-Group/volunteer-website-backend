import itertools
import pytest
import time
import psycopg2
import os
from datetime import date, datetime, time as Time
from sqlalchemy import create_engine, event, func, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Any, Protocol
from src.models import dbmodels


POSTGIS_URL = "postgresql+psycopg2://test:test@localhost:5434/test"


class Factories(Protocol):
    def volunteer(self, **overrides: Any) -> dbmodels.Volunteer: ...
    def admin(self, **overrides: Any) -> dbmodels.OrgAdmin: ...
    def organization(self, **overrides: Any) -> dbmodels.Organization: ...
    def event(self, **overrides: Any) -> dbmodels.Event: ...


# Configure pytest-docker to find docker-compose.yml
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Tell pytest-docker where to find docker-compose.yml"""
    return os.path.join(str(pytestconfig.rootdir), "src/tests/docker-compose.yml")


def is_postgres_responsive(url):
    """Check if PostgreSQL is accepting connections."""
    try:
        connection_string = url.replace("postgresql+psycopg2://", "postgresql://")
        conn = psycopg2.connect(connection_string)
        conn.close()
        return True
    except psycopg2.Error:
        return False


@pytest.fixture(scope="session")
def pg_engine(docker_services, docker_ip):
    """
    Session-scoped PostgreSQL engine using Docker.

    Spins up a PostGIS-enabled PostgreSQL container using pytest-docker.
    Ensures the database is reachable and PostGIS extension is created.
    """
    # Wait for PostgreSQL to become responsive
    # This implicitly starts the container defined in docker-compose.yml
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_postgres_responsive(POSTGIS_URL)
    )

    # Create SQLAlchemy engine with GeoAlchemy2 support
    engine = create_engine(
        POSTGIS_URL,
        future=True,
        echo=False,  # Set to True for SQL debugging
        plugins=["geoalchemy2"],  # Enable GeoAlchemy2 dialect
    )

    # Ensure PostGIS extension exists and create schema
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))

        # Create all tables
        dbmodels.Base.metadata.create_all(bind=conn)

    yield engine

    # Cleanup: drop all tables and dispose engine
    with engine.begin() as conn:
        dbmodels.Base.metadata.drop_all(bind=conn)
    engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    """
    Function-scoped session with automatic rollback.

    Uses nested transactions (SAVEPOINTs) to ensure complete isolation
    between tests. Each test gets a clean database state, and changes
    are rolled back after the test completes.
    """
    # Create a connection that persists for the test
    connection = pg_engine.connect()

    # Begin an outer transaction
    outer = connection.begin()

    # Create session bound to this connection
    SessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    session = SessionLocal()

    # Begin a nested transaction (SAVEPOINT)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        """
        Automatically restart the SAVEPOINT after each commit/rollback
        within the test. This ensures that test code can use db_session.commit()
        naturally, while we still roll back everything at the end.
        """
        if not connection.in_nested_transaction():
            connection.begin_nested()

    try:
        yield session
    finally:
        # Cleanup: close session, rollback outer transaction, close connection
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def factories(db_session: Session) -> Factories:
    """
    Factory fixture for creating test data.

    Provides factory methods for creating Volunteers, OrgAdmins,
    Organizations, and Events with sensible defaults and the ability
    to override any field.
    """
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
            "start_time": Time(4, 30, 0),
            "end_time": Time(7, 30, 0),
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
                    # Use PostGIS POINT - note: (longitude, latitude) order!
                    coordinates=func.ST_SetSRID(
                        func.ST_MakePoint(-97.739758, 30.276513), 4326
                    ),
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
                    # Use PostGIS POINT
                    coordinates=func.ST_SetSRID(
                        func.ST_MakePoint(-97.739758, 30.276513), 4326
                    ),
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
                    # Use PostGIS POINT
                    coordinates=func.ST_SetSRID(
                        func.ST_MakePoint(-97.739758, 30.276513), 4326
                    ),
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
