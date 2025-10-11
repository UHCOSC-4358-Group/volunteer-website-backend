# Where we handle DB session / CRUD methods
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from ..models.models import VolunteerCreate, AdminCreate

# Just simple setup stuff here, we want to make it so our db connection isn't a singleton
# Instead we make an engine our singleton, which can create a session per request
# Better for concurrency and wtv

# As for our chosen postgreSQL db, i recommend Supabase's free tier, sounds like a good deal
# If you need schema examples, here's a link

SQLALCHEMY_DATABASE_URL = "YOUR_POSTGRES_URL_HERE"
PRODUCTION_MODE = True if os.environ["PROD"] == "TRUE" else False

# Once we implement our db, then we can uncomment these lines
"""
# engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Inherit from this base for the data models
Base = declarative_base()
"""


def get_db():
    if not PRODUCTION_MODE:
        return None

    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()


# Create our CRUD functions which pass in the database instance being used
# I'll create some ones we'll need, including some of the params


# CREATE Volunteer obj
# Check the obj for expected params ^^^
def create_volunteer(db, volunteer: VolunteerCreate): ...


# CREATE OrgAdmin obj
# Check the obj for expected params ^^^
def create_org_admin(db, volunteer: AdminCreate): ...
