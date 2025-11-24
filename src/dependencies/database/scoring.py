"""
Reusable scoring components for volunteer-event matching.

Each function returns a SQLAlchemy expression that can be composed into queries.
"""

from sqlalchemy import select, case, func, Enum, literal, and_
from sqlalchemy.orm import InstrumentedAttribute
from ...models import dbmodels, pydanticmodels
from typing import List


def skills_match_score(
    entity_id_column: InstrumentedAttribute,
    entity_skills_table: type,
    entity_skills_id_column: InstrumentedAttribute,
    target_skills: List[str],
    max_weight: int = 2,
):
    """
    Calculate skills matching score.

    Args:
        entity_id_column: The ID column to correlate (e.g., dbmodels.Volunteer.id)
        entity_skills_table: The skills table (e.g., dbmodels.VolunteerSkill)
        entity_skills_id_column: Foreign key in skills table (e.g., VolunteerSkill.volunteer_id)
        target_skills: List of skill names to match against
        max_weight: Maximum points for skills (caps the score)

    Returns:
        SQLAlchemy expression for skills score (0 to max_weight)

    Example:
        # For volunteers matching an event's skills:
        volunteer_skills_score = skills_match_score(
            dbmodels.Volunteer.id,
            dbmodels.VolunteerSkill,
            dbmodels.VolunteerSkill.volunteer_id,
            ["Cooking", "Cleaning"],
            max_weight=2
        )
    """
    skills_count_subquery = (
        select(func.count())
        .select_from(entity_skills_table)
        .where(entity_skills_id_column == entity_id_column)
        .where(entity_skills_table.skill.in_(target_skills))
        .correlate_except(entity_skills_table)
        .scalar_subquery()
    )

    # Cap at max_weight
    return case(
        (skills_count_subquery > max_weight, max_weight),
        else_=skills_count_subquery,
    )


def schedule_overlap_score(
    volunteer_id_column: InstrumentedAttribute,
    event_day,
    event_start_time,
    event_end_time,
    max_weight: int = 4,
):
    """
    Calculate schedule overlap score.

    Args:
        volunteer_id_column: The volunteer ID column to correlate (e.g., dbmodels.Volunteer.id)
        event_day: Event date
        event_start_time: Event start time
        event_end_time: Event end time
        max_weight: Maximum points for schedule overlap

    Returns:
        SQLAlchemy expression for schedule score (0 or max_weight)

    Example:
        schedule_score = schedule_overlap_score(
            dbmodels.Volunteer.id,
            event.day,
            event.start_time,
            event.end_time,
            max_weight=4
        )
    """
    day_expr = func.extract("isodow", event_day)

    day_match = dbmodels.VolunteerAvailableTime.day_of_week == day_expr

    schedules_overlap = (
        select(literal(True))
        .select_from(dbmodels.VolunteerAvailableTime)
        .where(
            and_(
                dbmodels.VolunteerAvailableTime.volunteer_id == volunteer_id_column,
                day_match,
                dbmodels.VolunteerAvailableTime.start_time <= event_end_time,
                dbmodels.VolunteerAvailableTime.end_time >= event_start_time,
            )
        )
        .correlate_except(dbmodels.VolunteerAvailableTime)
        .exists()
    )

    return case(
        (schedules_overlap, max_weight),
        else_=0,
    )


def distance_based_location_score(
    distance_expr,
    max_distance: float,
    max_weight: int = 4,
):
    """
    Calculate location score based on distance.

    Closer = higher score using linear interpolation:
    - At 0 distance: max_weight points
    - At max_distance: 0 points
    - Linearly interpolated in between

    Args:
        distance_expr: SQLAlchemy expression for distance (in km or miles)
        max_distance: Maximum search radius
        max_weight: Maximum points for location

    Returns:
        SQLAlchemy expression for location score (0 to max_weight)

    Example:
        # If volunteer is 5 miles away, max_distance=25, max_weight=4:
        # score = (1 - 5/25) * 4 = 0.8 * 4 = 3.2 points
    """
    # Calculate percentage: (max_distance - distance) / max_distance
    # This gives 1.0 at center, 0.0 at edge
    percentage = (literal(max_distance) - distance_expr) / literal(max_distance)

    # Multiply by max weight
    # Clamp between 0 and max_weight in case of rounding issues
    return case(
        (percentage <= 0, 0),
        (percentage >= 1, max_weight),
        else_=(percentage * max_weight),
    )
