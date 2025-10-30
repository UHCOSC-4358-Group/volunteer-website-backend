from sqlalchemy import (
    Integer,
    String,
    Enum as SAEnum,
    ForeignKey,
    CheckConstraint,
    Text,
    Time,
    Date,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from typing import List
from .pydanticmodels import EventUrgency, DayOfWeek

Base = declarative_base()


class Volunteer(Base):
    __tablename__ = "volunteer"
    __table_args__ = (
        CheckConstraint(
            "user_type = 'volunteer'", name="ck_user_type_must_be_volunteer"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)
    location: Mapped[str] = mapped_column(String(255))
    user_type: Mapped[str] = mapped_column(
        String(9), default="volunteer", server_default="volunteer"
    )

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

    times_available: Mapped[List["VolunteerAvailableTime"]] = relationship(
        back_populates="volunteer", cascade="all, delete-orphan", passive_deletes=True
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


class VolunteerAvailableTime(Base):
    __tablename__ = "volunteer_weekly_schedule"
    __table_args__ = (
        CheckConstraint(
            "start_time < end_time", name="ck_schedule_start_time_le_end_time"
        ),
    )
    volunteer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("volunteer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    start_time: Mapped[Time] = mapped_column(Time, primary_key=True)
    end_time: Mapped[Time] = mapped_column(Time)
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SAEnum(DayOfWeek, name="schedule_day_of_week"), primary_key=True, index=True
    )

    volunteer: Mapped["Volunteer"] = relationship(back_populates="times_available")


class Organization(Base):
    __tablename__ = "organization"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)

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
    __table_args__ = (
        CheckConstraint("user_type = 'admin'", name="ck_user_type_must_be_admin"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)
    user_type: Mapped[str] = mapped_column(
        String(5), default="admin", server_default="admin"
    )
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
        CheckConstraint("start_time <= end_time", name="ck_event_has_nonneg_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    day: Mapped[Date] = mapped_column(Date)
    start_time: Mapped[Time] = mapped_column(Time)
    end_time: Mapped[Time] = mapped_column(Time)
    urgency: Mapped[EventUrgency] = mapped_column(
        SAEnum(EventUrgency, name="event_urgency_type"),
        default=EventUrgency.LOW,
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
