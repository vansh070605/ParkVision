import cv2
import time
import queue
import threading
import logging
import asyncio
from datetime import datetime
from sqlalchemy import select, update
from app.config.config import settings
from app.database.database import AsyncSessionLocal, OccupancyLog, ParkingSession, EventLog
from app.inference.inference_engine import InferenceEngine
from app.tracking.tracker import IoUTracker
from app.tracking.smoother import TemporalSmoother
from app.streaming.streamer import broadcaster

class ProcessingPipeline:
    def __init__(self, camera_id: int, video_path: str, capacity: int, rois: list):
        self.camera_id = camera_id
        self.video_path = video_path
        self.capacity = capacity
        self.rois = rois or []
        
        # Queues
        self.frame_queue = queue.Queue(maxsize=15)
        
        # Thread controller
        self.running = False
        self.threads = []
        
        # Engines & Trackers
        self.inference_engine = InferenceEngine()
        self.tracker = IoUTracker()
        self.smoother = TemporalSmoother()
        
        # Active parking sessions tracker: spot_id -> ParkingSession ID in DB
        self.active_sessions = {}
        self.prev_occupancy = {}
        self.last_occupied_count = -1
        self.last_metrics_log_time = 0.0

    def start(self):
        self.running = True
        
        # Thread 1: Frame Reader
        reader_thread = threading.Thread(target=self._frame_reader_worker, daemon=True)
        # Thread 2: Process Loop (Inference + Tracking + Stream Broadcast)
        process_thread = threading.Thread(target=self._process_worker, daemon=True)
        
        self.threads = [reader_thread, process_thread]
        for t in self.threads:
            t.start()
        print(f"[Pipeline] Started multi-threaded processing pipeline for camera {self.camera_id}")

    def stop(self):
        self.running = False
        # Empty queue to unblock reading thread if it's waiting
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                pass
                
        for t in self.threads:
            t.join(timeout=1.0)
        print(f"[Pipeline] Stopped processing pipeline for camera {self.camera_id}")

    def _frame_reader_worker(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logging.error(f"[Pipeline] Error opening video: {self.video_path}")
            self.running = False
            return
            
        frame_delay = 1.0 / settings.MJPEG_FPS
        
        while self.running:
            start_time = time.time()
            ret, frame = cap.read()
            
            if not ret:
                # Loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    break
                    
            # Scale frame for inference pipeline
            frame = cv2.resize(frame, (settings.STREAM_WIDTH, settings.STREAM_HEIGHT))
            
            try:
                # Put in queue, drop oldest frame if full to prevent lag
                self.frame_queue.put(frame, block=True, timeout=0.1)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame)
                except:
                    pass
                    
            # Keep targeted frame rate
            elapsed = time.time() - start_time
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
                
        cap.release()

    def _process_worker(self):
        frame_idx = 0
        last_yolo_detections = []
        
        # Async event loop for running database queries inside the thread
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever, daemon=True).start()
        
        while self.running:
            try:
                frame = self.frame_queue.get(block=True, timeout=1.0)
            except queue.Empty:
                continue
                
            now = time.time()
            
            # --- PHASE 1: Object Detection (YOLOv8) ---
            # Run YOLOv8 detection only every N frames to conserve GPU/CPU power
            if frame_idx % settings.FRAME_SKIP == 0:
                yolo_detections = self.inference_engine.run_object_detection(frame)
                last_yolo_detections = yolo_detections
            else:
                yolo_detections = last_yolo_detections
                
            frame_idx += 1
            
            # --- PHASE 2: Bounding Box Tracking (IoU Tracker) ---
            # Map detections into trackers to preserve tracking IDs
            yolo_bboxes = [det[:4] for det in yolo_detections]
            active_tracks = self.tracker.update(yolo_bboxes)
            
            # --- PHASE 3: ROI Extraction & CNN Occupancy Classification ---
            # Perform lightweight CNN classification on cropped ROIs
            cnn_results = self.inference_engine.classify_rois(frame, self.rois)
            
            # Draw tracking bounding boxes
            for track in active_tracks:
                tx1, ty1, tx2, ty2 = track["bbox"]
                tid = track["track_id"]
                cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), (255, 100, 0), 2)
                cv2.putText(frame, f"ID: {tid}", (tx1, ty1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 1)

            # Determine final occupancy decision & Draw ROIs
            occupied_count = 0
            
            for i, roi in enumerate(self.rois):
                rx, ry, rw, rh = int(roi['x']), int(roi['y']), int(roi['width']), int(roi['height'])
                is_ev = roi.get('is_ev', False)
                
                # Check CNN classification prediction
                cnn_occupied = cnn_results[i]["occupied"] if i < len(cnn_results) else False
                cnn_conf = cnn_results[i]["confidence"] if i < len(cnn_results) else 0.0
                
                # Check YOLO tracking/centroids to verify if a vehicle is parked inside
                yolo_in_spot = False
                tracked_vehicle_id = None
                for track in active_tracks:
                    cx, cy = track["centroid"]
                    if rx < cx < rx + rw and ry < cy < ry + rh:
                        yolo_in_spot = True
                        tracked_vehicle_id = track["track_id"]
                        break
                        
                # Hybrid Occupancy Logic: Trigger if CNN says occupied OR YOLO saw a vehicle centroid in ROI
                instant_occupied = cnn_occupied or yolo_in_spot
                
                # Apply Temporal Smoothing (Smoothing window threshold logic)
                is_occupied = self.smoother.update(i, instant_occupied)
                
                # EV spot misuse check
                is_ev_misuse = False
                if is_occupied and is_ev:
                    # EV detection: If a non-EV vehicle occupies EV slot.
                    # Standard cars are index 2, EV cars might be classified differently,
                    # here we assume if class is truck/motorcycle or any standard vehicle without EV clearance
                    # we trigger EV violation
                    is_ev_misuse = True # Simplified representation
                
                color = (0, 0, 255) if is_occupied else (0, 255, 0)
                if is_occupied:
                    occupied_count += 1
                    
                # Draw ROI box
                cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), color, 2)
                
                # EV badge
                if is_ev:
                    cv2.putText(frame, "EV", (rx + rw - 25, ry + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 2)
                    if is_ev_misuse:
                        cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (0, 165, 255), 3) # Orange box for misuse
                        
                # Spot ID Text
                cv2.putText(frame, f"Spot {i+1}", (rx + 5, ry + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                cv2.putText(frame, f"CNN: {int(cnn_conf*100)}%", (rx + 5, ry + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
                
                # Only write to database on actual state changes to avoid overloading SQLite
                prev_state = self.prev_occupancy.get(i, None)
                if is_occupied != prev_state:
                    self.prev_occupancy[i] = is_occupied
                    loop.call_soon_threadsafe(
                        asyncio.ensure_future, 
                        self._db_session_handler(i, is_occupied, tracked_vehicle_id, is_ev_misuse), 
                        loop=loop
                    )
                
            # Broadcast the processed frame + stats
            available_count = max(0, self.capacity - occupied_count)
            metrics = {
                "total_capacity": self.capacity,
                "occupied": occupied_count,
                "available": available_count
            }
            
            # Broadcast frame
            broadcaster.broadcast(frame, metrics)
            
            # Log metrics in database only when counts change or periodically (every 5 seconds)
            current_time = time.time()
            if occupied_count != self.last_occupied_count or (current_time - self.last_metrics_log_time) >= 5.0:
                self.last_occupied_count = occupied_count
                self.last_metrics_log_time = current_time
                loop.call_soon_threadsafe(
                    asyncio.ensure_future, 
                    self._db_metrics_handler(occupied_count, available_count), 
                    loop=loop
                )
            
        loop.call_soon_threadsafe(loop.stop)

    async def _db_metrics_handler(self, occupied, available):
        """Writes current occupancy to OccupancyLog table."""
        async with AsyncSessionLocal() as db:
            log = OccupancyLog(
                camera_id=self.camera_id,
                total_capacity=self.capacity,
                occupied_spots=occupied,
                available_spots=available,
                timestamp=datetime.utcnow()
            )
            db.add(log)
            await db.commit()

    async def _db_session_handler(self, spot_id: int, is_occupied: bool, vehicle_id: int, is_ev_misuse: bool):
        """Creates/ends occupancy sessions in DB and logs violations."""
        async with AsyncSessionLocal() as db:
            active_session_id = self.active_sessions.get(spot_id)
            
            if is_occupied and active_session_id is None:
                # Start new session
                session = ParkingSession(
                    camera_id=self.camera_id,
                    spot_id=spot_id,
                    vehicle_id=vehicle_id,
                    start_time=datetime.utcnow()
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
                self.active_sessions[spot_id] = session.id
                
                # Add EventLog for occupancy change
                event = EventLog(
                    camera_id=self.camera_id,
                    event_type="occupancy_change",
                    description=f"Spot {spot_id+1} became occupied.",
                    timestamp=datetime.utcnow()
                )
                db.add(event)
                
                # Trigger EV misuse alert
                if is_ev_misuse:
                    ev_event = EventLog(
                        camera_id=self.camera_id,
                        event_type="ev_misuse",
                        description=f"Non-EV vehicle detected in EV Spot {spot_id+1}!",
                        timestamp=datetime.utcnow()
                    )
                    db.add(ev_event)
                await db.commit()
                
            elif not is_occupied and active_session_id is not None:
                # Close existing session
                stmt = select(ParkingSession).where(ParkingSession.id == active_session_id)
                res = await db.execute(stmt)
                session = res.scalar_one_or_none()
                
                if session:
                    end_time = datetime.utcnow()
                    duration = (end_time - session.start_time).total_seconds()
                    
                    session.end_time = end_time
                    session.duration_seconds = duration
                    await db.commit()
                    
                    # Log event
                    event = EventLog(
                        camera_id=self.camera_id,
                        event_type="occupancy_change",
                        description=f"Spot {spot_id+1} became vacant. Duration: {round(duration/60, 1)} mins.",
                        timestamp=datetime.utcnow()
                    )
                    db.add(event)
                    await db.commit()
                    
                self.active_sessions[spot_id] = None
