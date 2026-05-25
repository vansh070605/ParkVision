import cv2
import base64
from ultralytics import YOLO

# Load the YOLOv8 medium model for much better accuracy on overhead angles
model = YOLO("yolov8m.pt")

# COCO classes: 2 is 'car', 5 is 'bus', 7 is 'truck'
VEHICLE_CLASSES = [2, 5, 7]

def get_video_stream(video_path, capacity: int):
    is_image = video_path.lower().endswith(('.jpg', '.jpeg', '.png'))
    cap = None
    static_frame = None
    
    if is_image:
        static_frame = cv2.imread(video_path)
        if static_frame is None:
            print(f"Error opening image: {video_path}")
            return
    else:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error opening video: {video_path}")
            return

    while True:
        if is_image:
            frame = static_frame.copy()
        else:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    break
        
        # Run YOLOv8 inference with a lower confidence threshold for overhead shots
        results = model(frame, classes=VEHICLE_CLASSES, conf=0.15, iou=0.45, verbose=False)
        
        occupied_count = 0
        for r in results:
            boxes = r.boxes
            for box in boxes:
                occupied_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                
                # Draw bounding box (red for occupied)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"Vehicle {conf:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        available_count = max(0, capacity - occupied_count)
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        metrics = {
            "total_capacity": capacity,
            "occupied": occupied_count,
            "available": available_count
        }
        
        yield frame_base64, metrics
