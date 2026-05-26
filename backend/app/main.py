import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.config import settings
from app.database.database import init_db
from app.api.endpoints import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Grade AI Smart Parking Analytics Platform",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    # Initialize directory structure
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("weights", exist_ok=True)
    
    # Initialize SQL database tables
    print("[Main] Initializing database connection...")
    await init_db()
    print("[Main] Database tables verified/initialized successfully.")

@app.get("/")
async def root():
    return {"message": "ParkVision AI Platform is online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
