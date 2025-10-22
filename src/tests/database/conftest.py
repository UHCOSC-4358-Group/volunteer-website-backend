import itertools
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Protocol, Optional
from src.models import dbmodels


class Factories(Protocol):
    def volunteer(self, *, email: Optional[str] = None) -> dbmodels.Volunteer: ...
    def organization(self, *, name: Optional[str] = None) -> dbmodels.Organization: ...
    def event(
        self,
        *,
        org: Optional[dbmodels.Organization] = None,
        capacity: int = 5,
        name: Optional[str] = None,
    ) -> dbmodels.Event: ...


engine = create_engine("sqlite+pysqlite:///:memory:", future=True)


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

    class F:
        def volunteer(self, *, email=None):
            n = next(counter)
            v = dbmodels.Volunteer(
                email=email or f"user{n}@example.com",
                password="x",
                first_name=f"First{n}",
                last_name=f"Last{n}",
                description="",
                image_url="",
                location="Houston",
            )
            db_session.add(v)
            db_session.commit()
            return v

        def organization(self, *, name=None):
            n = next(counter)
            org = dbmodels.Organization(
                name=name or f"Org {n}",
                location="Houston",
                description="",
                image_url="",
            )
            db_session.add(org)
            db_session.commit()
            return org

        def event(self, *, org=None, capacity=5, name=None):
            if org is None:
                org = self.organization()
            n = next(counter)
            ev = dbmodels.Event(
                name=name or f"Event {n}",
                description="desc",
                location="Houston",
                urgency=dbmodels.EventUrgency.LOW,
                capacity=capacity,
                org_id=org.id,
            )
            db_session.add(ev)
            db_session.commit()
            return ev

    return F()
