import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ParkVision AI Platform"
    API_V1_STR: str = "/api/v1"
    
    # DB configuration
    # Default to local SQLite database if Postgres is not set up
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./parkvision.db")
    
    # YOLO & CNN Models
    YOLO_MODEL_PATH: str = "yolov8m.pt"
    CUSTOM_WEIGHTS_DIR: str = "runs/parkvision_model/weights"
    CNN_MODEL_PATH: str = "weights/cnn_occupancy.pth"
    
    # Inference parameters
    CONFIDENCE_THRESHOLD: float = 0.25
    IOU_THRESHOLD: float = 0.45
    FRAME_SKIP: int = 2  # Run YOLO only every N frames
    
    # Streaming parameters
    MJPEG_FPS: int = 15
    STREAM_WIDTH: int = 1280
    STREAM_HEIGHT: int = 720
    
    # Temporal smoothing
    SMOOTHING_WINDOW: int = 10
    OCCUPIED_THRESHOLD: float = 0.70  # Spot occupied if occupied >= 70% of window
    EMPTY_THRESHOLD: float = 0.70     # Spot empty if empty >= 70% of window

    class Config:
        case_sensitive = True

settings = Settings()
