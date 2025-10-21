from sqlalchemy import (
    Integer,
    String,
    Enum as SAEnum,
    ForeignKey,
    CheckConstraint,
    Text,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from typing import List
from .models import EventUrgency

Base = declarative_base()


class Volunteer(Base):
    __tablename__ = "volunteer"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512))
    location: Mapped[str] = mapped_column(String(255))

    # One-to-many: Volunteer -> VolunteerSkill
    skills: Mapped[List["VolunteerSkill"]] = relationship(
        back_populates="volunteer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One-to-many to association object: Volunteer -> EventVolunteer
    events: Mapped[List["EventVolunteer"]] = relationship(
        back_populates="volunteer",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )


class VolunteerSkill(Base):
    __tablename__ = "volunteer_skill"
    # Composite PK (volunteer_id, skill)
    volunteer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("volunteer.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    skill: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Many-to-one: VolunteerSkill -> Volunteer
    volunteer: Mapped["Volunteer"] = relationship(back_populates="skills")


class Organization(Base):
    __tablename__ = "organization"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512))

    # One-to-many: Organization -> OrgAdmin (SET NULL on org delete)
    admins: Mapped[List["OrgAdmin"]] = relationship(
        back_populates="organization",
        passive_deletes=True,
    )

    # One-to-many: Organization -> Event (CASCADE on org delete)
    events: Mapped[List["Event"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class OrgAdmin(Base):
    __tablename__ = "organization_admin"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512))
    # org_id is set to NULL when organization is deleted
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Many-to-one: OrgAdmin -> Organization
    organization: Mapped["Organization"] = relationship(back_populates="admins")


class Event(Base):
    __tablename__ = "event"

    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_event_capacity_nonneg"),
        CheckConstraint("assigned >= 0", name="ck_event_assigned_nonneg"),
        CheckConstraint("assigned <= capacity", name="ck_event_assigned_le_capacity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    urgency: Mapped[EventUrgency] = mapped_column(
        SAEnum(EventUrgency, name="event_urgency_type"),
        default=EventUrgency.LOW,
        server_default=text("'Low'::event_urgency_type"),
        nullable=False,
    )
    assigned: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # If org is deleted, then all events are deleted
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Many-to-one: Event -> Organization
    organization: Mapped["Organization"] = relationship(back_populates="events")

    # One-to-many: Event -> EventSkill (delete-orphan on ORM, CASCADE on DB)
    needed_skills: Mapped[List["EventSkill"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One-to-many to association object: Event -> EventVolunteer
    volunteers: Mapped[List["EventVolunteer"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )


class EventSkill(Base):
    __tablename__ = "event_skill"
    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    skill: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Many-to-one: EventSkill -> Event
    event: Mapped["Event"] = relationship(back_populates="needed_skills")


class EventVolunteer(Base):
    __tablename__ = "event_volunteer"
    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"),
        primary_key=True,
    )
    volunteer_id: Mapped[int] = mapped_column(
        ForeignKey("volunteer.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Many-to-one: EventVolunteer -> (Volunteer, Event)
    volunteer: Mapped["Volunteer"] = relationship(back_populates="events")
    event: Mapped["Event"] = relationship(back_populates="volunteers")
