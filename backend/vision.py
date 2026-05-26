import cv2
import base64
import os
import json
from ultralytics import YOLO

# Check if custom trained weights exist
custom_weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs", "parkvision_model", "weights", "best.pt")
if os.path.exists(custom_weights_path):
    print(f"Loading custom trained YOLOv8 model from {custom_weights_path}")
    model = YOLO(custom_weights_path)
    # Custom models usually have a different class mapping (e.g. 0: 'car' or 'vehicle')
    # We allow all classes present in the custom model to be detected as vehicles
    VEHICLE_CLASSES = list(model.names.keys())
else:
    print("Loading pre-trained YOLOv8m model...")
    # Load the YOLOv8 medium model for much better accuracy on overhead angles
    model = YOLO("yolov8m.pt")
    # COCO classes: 2 is 'car', 5 is 'bus', 7 is 'truck'
    VEHICLE_CLASSES = [2, 5, 7]

def get_video_stream(video_path, capacity: int):
    is_image = video_path.lower().endswith(('.jpg', '.jpeg', '.png'))
    cap = None
    static_frame = None
    
    rois_path = video_path + "_rois.json"
    user_rois = []
    if os.path.exists(rois_path):
        with open(rois_path, 'r') as f:
            try:
                user_rois = json.load(f)
            except:
                pass
            
    if user_rois:
        capacity = len(user_rois)
    
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
        
        # Run YOLOv8 inference
        results = model(frame, classes=VEHICLE_CLASSES, conf=0.1, iou=0.45, imgsz=1280, verbose=False)
        
        vehicle_centers = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                vehicle_centers.append((cx, cy))

        # --- NOVELTY: Hybrid OpenCV Pixel Density + YOLO ---
        # 1. Convert to grayscale & blur
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 1)
        # 2. Adaptive Thresholding to find edges/shapes
        imgThres = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
        # 3. Clean up noise
        imgMedian = cv2.medianBlur(imgThres, 5)
        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

        occupied_count = 0
        
        if user_rois:
            for i, roi in enumerate(user_rois):
                rx, ry, rw, rh = int(roi['x']), int(roi['y']), int(roi['width']), int(roi['height'])
                
                # Check YOLO
                yolo_occupied = False
                for (cx, cy) in vehicle_centers:
                    if rx < cx < rx + rw and ry < cy < ry + rh:
                        yolo_occupied = True
                        break
                
                # Check Pixel Density (GFG Method)
                roi_crop = imgDilate[ry:ry+rh, rx:rx+rw]
                count = cv2.countNonZero(roi_crop)
                area = rw * rh
                density = count / area if area > 0 else 0
                
                # If edges take up more than 15% of the spot, or YOLO saw a car
                density_occupied = density > 0.15
                is_occupied = yolo_occupied or density_occupied
                
                color = (0, 0, 255) if is_occupied else (0, 255, 0) # Red if occupied, Green if free
                if is_occupied:
                    occupied_count += 1
                    
                # Draw ROI box
                cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), color, 2)
                
                # Draw UI Text Background
                cv2.rectangle(frame, (rx, ry - 20), (rx + 80, ry), color, cv2.FILLED)
                # Spot Name
                cv2.putText(frame, f"Spot {i+1}", (rx + 5, ry - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                # Draw Analytics inside the box
                cv2.putText(frame, f"D: {int(density*100)}%", (rx + 5, ry + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)
                if yolo_occupied:
                    cv2.putText(frame, "AI: YES", (rx + 5, ry + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)
        else:
            # Fallback if no ROIs were provided
            occupied_count = len(vehicle_centers)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
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

def auto_detect_spots(image_path):
    frame = cv2.imread(image_path)
    if frame is None:
        return []
    
    # Run YOLOv8 with very high sensitivity to catch all cars in the calibration frame
    results = model(frame, classes=VEHICLE_CLASSES, conf=0.05, iou=0.45, imgsz=1280, verbose=False)
    
    detected_rois = []
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            width = x2 - x1
            height = y2 - y1
            
            # Add some padding to make the spot slightly larger than the car
            padding_x = int(width * 0.1)
            padding_y = int(height * 0.1)
            
            x1_pad = max(0, x1 - padding_x)
            y1_pad = max(0, y1 - padding_y)
            width_pad = width + (padding_x * 2)
            height_pad = height + (padding_y * 2)
            
            detected_rois.append({
                "x": x1_pad,
                "y": y1_pad,
                "width": width_pad,
                "height": height_pad
            })
            
    return detected_rois
