import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey
from app.config.config import settings

# Create async engine
# Note: For SQLite we need special pool settings
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

class Camera(Base):
    __tablename__ = "cameras"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    rtsp_url: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    # Store ROIs as JSON (list of dicts with keys x, y, width, height, is_ev, etc.)
    rois: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) 
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class OccupancyLog(Base):
    __tablename__ = "occupancy_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    total_capacity: Mapped[int] = mapped_column(Integer)
    occupied_spots: Mapped[int] = mapped_column(Integer)
    available_spots: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)

class ParkingSession(Base):
    __tablename__ = "parking_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    spot_id: Mapped[int] = mapped_column(Integer, index=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # From tracking ID
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

class EventLog(Base):
    __tablename__ = "event_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True) # e.g. "illegal_parking", "prolonged_parking", "ev_misuse", "occupancy_change"
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    predicted_occupancy: Mapped[int] = mapped_column(Integer)
    prediction_time: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    target_time: Mapped[datetime.datetime] = mapped_column(DateTime, index=True) # Time point we are predicting

async def init_db():
    async with engine.begin() as conn:
        # Import sqlite driver conditionally if SQLite is used
        if is_sqlite:
            import aiosqlite
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
