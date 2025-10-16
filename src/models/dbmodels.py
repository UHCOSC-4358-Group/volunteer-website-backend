from sqlalchemy import Column, Integer, String, Enum, ForeignKey, CheckConstraint, Text
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class Volunteer(Base):
    __tablename__ = "volunteer"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    description = Column(Text)
    image_url = Column(String(512))
    location = Column(String(255))

    # One-to-many: Volunteer -> VolunteerSkill
    skills = relationship(
        "VolunteerSkill",
        back_populates="volunteer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One-to-many to association object: Volunteer -> EventVolunteer
    events = relationship(
        "EventVolunteer",
        back_populates="volunteer",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )


class VolunteerSkill(Base):
    __tablename__ = "volunteer_skill"
    # Composite PK (volunteer_id, skill)
    volunteer_id = Column(
        Integer,
        ForeignKey("volunteer.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    skill = Column(String(100), primary_key=True)

    # Many-to-one: VolunteerSkill -> Volunteer
    volunteer = relationship("Volunteer", back_populates="skills")


class Organization(Base):
    __tablename__ = "organization"
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String)
    image_url = Column(String(512))

    # One-to-many: Organization -> OrgAdmin (SET NULL on org delete)
    admins = relationship(
        "OrgAdmin",
        back_populates="organization",
        passive_deletes=True,
    )

    # One-to-many: Organization -> Event (CASCADE on org delete)
    events = relationship(
        "Event",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class OrgAdmin(Base):
    __tablename__ = "organization_admin"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    description = Column(String)
    image_url = Column(String(512))
    # org_id is set to NULL when organization is deleted
    org_id = Column(
        Integer,
        ForeignKey("organization.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Many-to-one: OrgAdmin -> Organization
    organization = relationship("Organization", back_populates="admins")


class EventUrgency(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Event(Base):
    __tablename__ = "event"

    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_event_capacity_nonneg"),
        CheckConstraint("assigned >= 0", name="ck_event_assigned_nonneg"),
        CheckConstraint("assigned <= capacity", name="ck_event_assigned_le_capacity"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=False)
    location = Column(String(255), nullable=False)
    urgency = Column(
        Enum(EventUrgency, name="event_urgency_type"),
        default=EventUrgency.LOW,
        nullable=False,
    )
    assigned = Column(Integer, nullable=False, default=0, server_default="0")
    capacity = Column(Integer, nullable=False)

    # If org is deleted, then all events are deleted
    org_id = Column(
        Integer,
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Many-to-one: Event -> Organization
    organization = relationship("Organization", back_populates="events")

    # One-to-many: Event -> EventSkill (delete-orphan on ORM, CASCADE on DB)
    needed_skills = relationship(
        "EventSkill",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One-to-many to association object: Event -> EventVolunteer
    volunteers = relationship(
        "EventVolunteer",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )


class EventSkill(Base):
    __tablename__ = "event_skill"
    event_id = Column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    skill = Column(String(100), primary_key=True)

    # Many-to-one: EventSkill -> Event
    event = relationship("Event", back_populates="needed_skills")


class EventVolunteer(Base):
    __tablename__ = "event_volunteer"
    event_id = Column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE"),
        primary_key=True,
    )
    volunteer_id = Column(
        Integer,
        ForeignKey("volunteer.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Many-to-one: EventVolunteer -> (Volunteer, Event)
    volunteer = relationship("Volunteer", back_populates="events")
    event = relationship("Event", back_populates="volunteers")
