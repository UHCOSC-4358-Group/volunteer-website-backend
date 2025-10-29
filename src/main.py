from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from .dependencies.database.config import lifespan
from .util.error import (
    http_exception_handler,
    validation_exception_error,
    catch_all_exceptions_middleware,
)

load_dotenv(dotenv_path=find_dotenv())

# Routers
from .routers import auth, event, org, volunteer


app = FastAPI(
    title="Volunteer Website API",
    description="Backend API for volunteer website",
    version="1.0.0",
    lifespan=lifespan,
)

# Error handling stuff
app.middleware("http")(catch_all_exceptions_middleware)

app.exception_handler(HTTPException)(http_exception_handler)

app.exception_handler(RequestValidationError)(validation_exception_error)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FIXME: CHANGE FOR PRODUCTION LATER
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
