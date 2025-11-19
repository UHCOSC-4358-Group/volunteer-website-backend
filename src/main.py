from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from .dependencies.database.config import lifespan
from .util.error import (
    http_exception_handler,
    validation_exception_error,
    ErrorHandlingMiddleware,
)
from .util.logging_config import setup_logging

load_dotenv(dotenv_path=find_dotenv())

# Routers
from .routers import auth, event, org, volunteer


setup_logging(log_level="INFO", log_file="errors.log")

app = FastAPI(
    title="Volunteer Website API",
    description="Backend API for volunteer website",
    version="1.0.0",
    lifespan=lifespan,
)

# Error handling stuff
app.add_middleware(ErrorHandlingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # FIXME: CHANGE FOR PRODUCTION LATER
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.exception_handler(HTTPException)(http_exception_handler)

app.exception_handler(RequestValidationError)(validation_exception_error)

# /auth
app.include_router(auth.router)

# /event
app.include_router(event.router)

# /org
app.include_router(org.router)

# /volunteer
app.include_router(volunteer.router)


# All sign up methods should return a id, making it


@app.get("/vol")
async def all_volunteers():
    return ["N/A"]


@app.get("/")
async def root():
    return {"message": "Welcome to Volunteer Website API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
