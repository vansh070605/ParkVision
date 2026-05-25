from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import json
import shutil
from vision import get_video_stream, auto_detect_spots

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), rois: str = Form(None)):
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if rois:
        rois_path = os.path.join(UPLOADS_DIR, file.filename + "_rois.json")
        with open(rois_path, "w") as f:
            f.write(rois)
            
    return {"filename": file.filename, "message": "File uploaded successfully"}

@app.post("/auto-calibrate")
async def auto_calibrate(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOADS_DIR, "calibration_" + file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    detected_rois = auto_detect_spots(file_path)
    return {"rois": detected_rois}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, filename: str, capacity: int = 10):
    await websocket.accept()
    
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        # Fallback if file doesn't exist
        file_path = os.path.join(BASE_DIR, "sample_video.mp4")
        if not os.path.exists(file_path):
             import subprocess
             subprocess.run(["python", os.path.join(BASE_DIR, "create_dummy_video.py")])
    
    stream = get_video_stream(file_path, capacity)
    
    try:
        for frame_base64, metrics in stream:
            payload = {
                "frame": frame_base64,
                "metrics": metrics
            }
            await websocket.send_text(json.dumps(payload))
            # Control frame rate roughly
            await asyncio.sleep(1/30)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
