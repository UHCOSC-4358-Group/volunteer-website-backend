from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Volunteer Website API",
    description="Backend API for volunteer website",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FIXME: CHANGE FOR PRODUCTION LATER
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to Volunteer Website API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
