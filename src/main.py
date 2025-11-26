from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from .dependencies.database.config import lifespan
from .util.error import ErrorHandlingMiddleware, validation_exception_handler
from .util.logging_config import setup_logging

load_dotenv(dotenv_path=find_dotenv())

# Routers
from .routers import auth, event, org, volunteer, notifications


setup_logging(log_level="INFO", log_file="errors.log")

app = FastAPI(
    title="Volunteer Website API",
    description="Backend API for volunteer website",
    version="1.0.0",
    lifespan=lifespan,
)

# Error handling stuff
app.add_middleware(ErrorHandlingMiddleware)
app.exception_handler(RequestValidationError)(validation_exception_handler)

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# /notifications
app.include_router(notifications.router)


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
