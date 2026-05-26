import os
import json
import shutil
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.config.config import settings
from app.database.database import get_db, Camera, OccupancyLog, EventLog, PredictionLog
from app.calibration.auto_calibrate import detect_parking_slots_contours
from app.services.pipeline import ProcessingPipeline
from app.streaming.streamer import broadcaster
from app.analytics.analytics_engine import AnalyticsService
from app.models.lstm_predictor import LSTMPredictorService
from pydantic import BaseModel

router = APIRouter()

# Global dictionary to track active pipelines
active_pipelines = {}

# Instantiate LSTM predictor service
lstm_predictor = LSTMPredictorService()

# Pydantic schemas
class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    capacity: int
    rois: List[dict] = []

@router.post("/upload")
async def upload_media(file: UploadFile = File(...), rois: str = Form(None)):
    """Uploads a video or image feed file to the system."""
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_path = os.path.join(uploads_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if rois:
        rois_path = os.path.join(uploads_dir, file.filename + "_rois.json")
        with open(rois_path, "w") as f:
            f.write(rois)
            
    return {"filename": file.filename, "message": "File uploaded successfully"}

@router.post("/auto-calibrate")
async def auto_calibrate(file: UploadFile = File(...)):
    """Runs Canny-contour based calibration on a parking lot image."""
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, "calibration_" + file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    detected_rois = detect_parking_slots_contours(file_path)
    
    # Clean up file after run
    try:
        os.remove(file_path)
    except:
        pass
        
    return {"rois": detected_rois}

# CAMERA MANAGEMENT
@router.post("/cameras")
async def create_camera(cam_data: CameraCreate, db: AsyncSession = Depends(get_db)):
    # Check if a camera with the same name already exists to avoid UNIQUE constraint violations
    stmt = select(Camera).where(Camera.name == cam_data.name)
    res = await db.execute(stmt)
    existing_camera = res.scalar_one_or_none()
    
    if existing_camera:
        # If it exists, update it with the new configuration
        existing_camera.rtsp_url = cam_data.rtsp_url
        existing_camera.capacity = cam_data.capacity
        existing_camera.rois = cam_data.rois
        await db.commit()
        await db.refresh(existing_camera)
        return existing_camera

    camera = Camera(
        name=cam_data.name,
        rtsp_url=cam_data.rtsp_url,
        capacity=cam_data.capacity,
        rois=cam_data.rois
    )
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return camera

@router.get("/cameras")
async def get_cameras(db: AsyncSession = Depends(get_db)):
    stmt = select(Camera)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    # Stop pipeline first if running
    if camera_id in active_pipelines:
        active_pipelines[camera_id].stop()
        del active_pipelines[camera_id]
        
    stmt = delete(Camera).where(Camera.id == camera_id)
    await db.execute(stmt)
    await db.commit()
    return {"message": "Camera deleted successfully"}

# PIPELINE ACTIONS
@router.post("/cameras/{camera_id}/start")
async def start_camera_pipeline(camera_id: int, db: AsyncSession = Depends(get_db)):
    """Starts the multi-threaded video inference pipeline for a camera."""
    if camera_id in active_pipelines:
        return {"message": "Pipeline already running"}
        
    stmt = select(Camera).where(Camera.id == camera_id)
    res = await db.execute(stmt)
    camera = res.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    # Check if RTSP url is actually a local file in uploads directory
    video_path = camera.rtsp_url
    if not video_path.startswith("rtsp://") and not os.path.exists(video_path):
        # Fallback to uploads path
        uploads_path = os.path.join("uploads", camera.rtsp_url)
        if os.path.exists(uploads_path):
            video_path = uploads_path
        else:
            # Fallback if no file exists
            video_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sample_video.mp4")
            if not os.path.exists(video_path):
                 import subprocess
                 subprocess.run(["python", "create_dummy_video.py"])
                 
    pipeline = ProcessingPipeline(camera.id, video_path, camera.capacity, camera.rois)
    pipeline.start()
    active_pipelines[camera_id] = pipeline
    return {"message": "Pipeline started successfully"}

@router.post("/cameras/{camera_id}/stop")
async def stop_camera_pipeline(camera_id: int):
    if camera_id not in active_pipelines:
        return {"message": "Pipeline is not running"}
        
    active_pipelines[camera_id].stop()
    del active_pipelines[camera_id]
    return {"message": "Pipeline stopped successfully"}

# STREAMING CONTROLLERS
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket streaming base64 JPEGs and statistics telemetry."""
    await websocket.accept()
    queue = broadcaster.subscribe()
    
    try:
        while True:
            # Fetch processed frames from the broadcaster queue
            payload = await queue.get()
            
            response_data = {
                "frame": payload["frame"],
                "metrics": payload["metrics"]
            }
            await websocket.send_text(json.dumps(response_data))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] Stream error: {e}")
    finally:
        broadcaster.unsubscribe(queue)

@router.get("/stream")
async def mjpeg_stream_endpoint():
    """MJPEG HTTP Streaming endpoint for easy standard browser players."""
    queue = broadcaster.subscribe()
    
    async def frame_generator():
        try:
            while True:
                payload = await queue.get()
                frame_bytes = payload["raw_bytes"]
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
                       + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"[MJPEG] Stream dropped: {e}")
        finally:
            broadcaster.unsubscribe(queue)
            
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ANALYTICS ENDPOINTS
@router.get("/analytics/{camera_id}/trends")
async def get_trends(camera_id: int, hours: int = 24, db: AsyncSession = Depends(get_db)):
    return await AnalyticsService.get_historical_trends(db, camera_id, hours)

@router.get("/analytics/{camera_id}/peak-hours")
async def get_peaks(camera_id: int, db: AsyncSession = Depends(get_db)):
    return await AnalyticsService.get_peak_hours(db, camera_id)

@router.get("/analytics/{camera_id}/duration")
async def get_duration(camera_id: int, db: AsyncSession = Depends(get_db)):
    avg_minutes = await AnalyticsService.get_average_duration(db, camera_id)
    return {"average_duration_minutes": avg_minutes}

@router.get("/analytics/{camera_id}/heatmap")
async def get_heatmap(camera_id: int, db: AsyncSession = Depends(get_db)):
    return await AnalyticsService.get_spatial_heatmap(db, camera_id)

@router.get("/analytics/{camera_id}/events")
async def get_events(camera_id: int, limit: int = 20, db: AsyncSession = Depends(get_db)):
    stmt = select(EventLog).where(EventLog.camera_id == camera_id).order_by(EventLog.timestamp.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

# PREDICTIONS ENDPOINT
@router.get("/predictions/{camera_id}")
async def get_predictions(camera_id: int, db: AsyncSession = Depends(get_db)):
    """Generates future occupancy counts (+15m, +30m, +1h) using the LSTM model."""
    stmt = select(Camera).where(Camera.id == camera_id)
    res = await db.execute(stmt)
    camera = res.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    # Get last 12 logs (1 hour history) from DB
    stmt_logs = select(OccupancyLog.occupied_spots).where(OccupancyLog.camera_id == camera_id).order_by(OccupancyLog.timestamp.desc()).limit(12)
    res_logs = await db.execute(stmt_logs)
    recent_occupancies = res_logs.scalars().all()
    recent_occupancies.reverse() # Sort chronologically
    
    # Call LSTM model
    pred_results = lstm_predictor.predict_occupancy(recent_occupancies, camera.capacity)
    
    # Save predictions to database
    now = datetime.utcnow()
    p15 = PredictionLog(camera_id=camera_id, predicted_occupancy=pred_results["prediction_15m"], target_time=now + timedelta(minutes=15))
    p30 = PredictionLog(camera_id=camera_id, predicted_occupancy=pred_results["prediction_30m"], target_time=now + timedelta(minutes=30))
    p60 = PredictionLog(camera_id=camera_id, predicted_occupancy=pred_results["prediction_60m"], target_time=now + timedelta(hours=1))
    
    db.add_all([p15, p30, p60])
    await db.commit()
    
    return pred_results

@router.post("/predictions/{camera_id}/retrain")
async def retrain_predictions(camera_id: int, db: AsyncSession = Depends(get_db)):
    """Triggers LSTM training on recent database logs."""
    success = await lstm_predictor.retrain_on_db(db)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient database logs to retrain model yet.")
    return {"message": "Model retrained successfully."}
