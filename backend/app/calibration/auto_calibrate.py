import cv2
import numpy as np
import os
from ultralytics import YOLO
import torch

# PyTorch 2.6+ compatibility patch to bypass weights_only default behavior for YOLOv8
try:
    _orig_load = torch.load
    def new_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _orig_load(*args, **kwargs)
    torch.load = new_load
except Exception:
    pass

def compute_iou(box1, box2):
    """Computes Intersection over Union (IoU) between two boxes: [x, y, w, h]"""
    x1_1, y1_1, x2_1, y2_1 = box1[0], box1[1], box1[0] + box1[2], box1[1] + box1[3]
    x1_2, y1_2, x2_2, y2_2 = box2[0], box2[1], box2[0] + box2[2], box2[1] + box2[3]
    
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y1_2 + box2[3], y1_1 + box1[3]) # min of y2s
    
    inter_area = max(0, xi2 - xi1) * max(0, min(y2_1, y2_2) - yi1)
    box1_area = box1[2] * box1[3]
    box2_area = box2[2] * box2[3]
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0

def apply_nms(boxes, iou_threshold=0.3):
    """Filters heavily overlapping boxes using Non-Maximum Suppression"""
    if not boxes:
        return []
    
    # Sort by area descending (prefer larger structured spots over fragments)
    boxes = sorted(boxes, key=lambda b: b['width'] * b['height'], reverse=True)
    keep = []
    
    for box in boxes:
        overlap = False
        box_coords = [box['x'], box['y'], box['width'], box['height']]
        for kept in keep:
            kept_coords = [kept['x'], kept['y'], kept['width'], kept['height']]
            if compute_iou(box_coords, kept_coords) > iou_threshold:
                overlap = True
                break
        if not overlap:
            keep.append(box)
            
    return keep

def run_yolo_fallback(image, image_path: str) -> list:
    """
    Fallback vehicle-centric detector: runs YOLOv8 and generates ROIs around cars.
    """
    print("[Calibration Fallback] Running YOLO-based auto-calibration...")
    
    # Locate weights dynamically
    weights_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    custom_weights_path = os.path.join(weights_dir, "runs", "parkvision_model", "weights", "best.pt")
    
    if os.path.exists(custom_weights_path):
        model = YOLO(custom_weights_path)
        classes = list(model.names.keys())
    else:
        # Load pre-trained and include cell phone (67), toaster (70), tv (62) for top-down views
        yolo_path = os.path.join(weights_dir, "yolov8m.pt")
        if not os.path.exists(yolo_path):
            yolo_path = "yolov8m.pt"
        model = YOLO(yolo_path)
        classes = [2, 5, 7, 62, 67, 70]
        
    results = model(image, classes=classes, conf=0.08, imgsz=1280, verbose=False)
    rois = []
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w = x2 - x1
            h = y2 - y1
            
            # Place a typical parking slot size around the vehicle center
            # Adding 10% padding
            pad_x = int(w * 0.1)
            pad_y = int(h * 0.1)
            rx = max(0, x1 - pad_x)
            ry = max(0, y1 - pad_y)
            rw = w + 2 * pad_x
            rh = h + 2 * pad_y
            
            rois.append({
                "x": int(rx),
                "y": int(ry),
                "width": int(rw),
                "height": int(rh),
                "is_ev": False
            })
            
    return apply_nms(rois, iou_threshold=0.3)

def detect_parking_slots_contours(image_path: str) -> list:
    """
    Robust parking slot detector using:
      1. CLAHE & bilateral filtering.
      2. Hough Line extraction.
      3. YOLO context filtering.
      4. 1D RANSAC Grid Fitting & Spacing Mode extraction.
      5. Geometry validation & NMS.
    """
    image = cv2.imread(image_path)
    if image is None:
        return []
        
    h_img, w_img = image.shape[:2]
    image_area = h_img * w_img
    
    # Define debug directory
    debug_dir = os.path.dirname(image_path)
    debug_path = os.path.join(debug_dir, "debug_calibration.jpg")
    
    # ------------------ STEP 1: PREPROCESSING ------------------
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast with CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray)
    
    # Smooth pavement texture while keeping line edges crisp
    blurred = cv2.GaussianBlur(gray_clahe, (9, 9), 0)
    smoothed = cv2.bilateralFilter(blurred, 9, 75, 75)
    
    # Detect edges
    edges = cv2.Canny(smoothed, 50, 150)
    
    # ------------------ STEP 2: RUN YOLO FOR CONTEXT FILTERING ------------------
    weights_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    custom_weights_path = os.path.join(weights_dir, "runs", "parkvision_model", "weights", "best.pt")
    
    if os.path.exists(custom_weights_path):
        model = YOLO(custom_weights_path)
        classes = list(model.names.keys())
    else:
        yolo_path = os.path.join(weights_dir, "yolov8m.pt")
        if not os.path.exists(yolo_path):
            yolo_path = "yolov8m.pt"
        model = YOLO(yolo_path)
        classes = [2, 5, 7, 62, 67, 70]
        
    vehicle_boxes = []
    try:
        results = model(image, classes=classes, conf=0.1, imgsz=1280, verbose=False)
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                vehicle_boxes.append((x1, y1, x2, y2))
    except Exception as e:
        print(f"[Calibration] YOLO context detection failed: {e}")
        
    # ------------------ STEP 3: HOUGH LINE DETECTION & FILTERING ------------------
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180, threshold=50, minLineLength=80, maxLineGap=20)
    
    if lines is None or len(lines) == 0:
        return run_yolo_fallback(image, image_path)
        
    detected_lines = []
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
        if angle < 0:
            angle += 180
        angles.append(angle)
        detected_lines.append((x1, y1, x2, y2, length, angle))
        
    # Extract dominant orientation for vertical divider lines (70-110 degrees)
    vert_angles = [a for a in angles if 70 <= a <= 110]
    if len(vert_angles) > 0:
        hist, bin_edges = np.histogram(vert_angles, bins=40, range=(70, 110))
        dominant_bin = np.argmax(hist)
        dominant_angle = (bin_edges[dominant_bin] + bin_edges[dominant_bin + 1]) / 2.0
    else:
        dominant_angle = 90.0
        
    # Filter by dominant angle AND ignore lines lying inside the inner 70% of vehicles
    filtered_lines = []
    for x1, y1, x2, y2, length, angle in detected_lines:
        if abs(angle - dominant_angle) > 10.0:
            continue
            
        line_x = (x1 + x2) / 2.0
        line_y_mid = (y1 + y2) / 2.0
        
        is_inside_car = False
        for (cx1, cy1, cx2, cy2) in vehicle_boxes:
            car_w = cx2 - cx1
            inner_x1 = cx1 + 0.15 * car_w
            inner_x2 = cx2 - 0.15 * car_w
            
            if (inner_x1 <= line_x <= inner_x2) and (cy1 <= line_y_mid <= cy2):
                is_inside_car = True
                break
                
        if not is_inside_car:
            filtered_lines.append((x1, y1, x2, y2))
            
    if len(filtered_lines) < 3:
        return run_yolo_fallback(image, image_path)
        
    # ------------------ STEP 4: COLLINEAR LINE MERGING ------------------
    merged_lines = []
    used = set()
    for i in range(len(filtered_lines)):
        if i in used:
            continue
        x1_i, y1_i, x2_i, y2_i = filtered_lines[i]
        curr_x = (x1_i + x2_i) / 2.0
        curr_y_min = min(y1_i, y2_i)
        curr_y_max = max(y1_i, y2_i)
        
        for j in range(i + 1, len(filtered_lines)):
            if j in used:
                continue
            x1_j, y1_j, x2_j, y2_j = filtered_lines[j]
            other_x = (x1_j + x2_j) / 2.0
            other_y_min = min(y1_j, y2_j)
            other_y_max = max(y1_j, y2_j)
            
            if abs(curr_x - other_x) < 20:
                gap = max(0, other_y_min - curr_y_max) if other_y_min > curr_y_max else max(0, curr_y_min - other_y_max)
                if gap < 60:
                    curr_x = (curr_x + other_x) / 2.0
                    curr_y_min = min(curr_y_min, other_y_min)
                    curr_y_max = max(curr_y_max, other_y_max)
                    used.add(j)
                    
        merged_lines.append((int(curr_x), int(curr_y_min), int(curr_x), int(curr_y_max)))
        used.add(i)
        
    # ------------------ STEP 5: ROW CLUSTERING ------------------
    rows = []
    for line in merged_lines:
        x1, y1, x2, y2 = line
        added_to_row = False
        for row in rows:
            row_y_min = min(r[1] for r in row)
            row_y_max = max(r[3] for r in row)
            overlap = max(0, min(y2, row_y_max) - max(y1, row_y_min))
            length = y2 - y1
            if overlap > 0.4 * length or overlap > 0.4 * (row_y_max - row_y_min):
                row.append(line)
                added_to_row = True
                break
        if not added_to_row:
            rows.append([line])
            
    # ------------------ STEP 6: 1D RANSAC GRID FITTING & SLOT GENERATION ------------------
    debug_img = image.copy()
    rois = []
    
    # Overlay YOLO vehicle boxes in red for visual debugging
    for (cx1, cy1, cx2, cy2) in vehicle_boxes:
        cv2.rectangle(debug_img, (cx1, cy1), (cx2, cy2), (0, 0, 255), 2)
        
    colors = [(0, 255, 0), (255, 165, 0), (0, 255, 255), (255, 0, 255)]
    
    for r_idx, row in enumerate(rows):
        if len(row) < 3:
            continue
            
        color = colors[r_idx % len(colors)]
        row = sorted(row, key=lambda l: l[0])
        
        xs = [l[0] for l in row]
        y_starts = [min(l[1], l[3]) for l in row]
        y_ends = [max(l[1], l[3]) for l in row]
        
        row_y_start = int(np.median(y_starts))
        row_y_end = int(np.median(y_ends))
        row_h = row_y_end - row_y_start
        
        # Calculate spacing mode using pairwise differences
        dxs = []
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                dxs.append(xs[j] - xs[i])
                
        # Find dominant width in a realistic range (100 - 350 pixels)
        valid_dxs = [d for d in dxs if 100 <= d <= 350]
        if len(valid_dxs) == 0:
            valid_dxs = [d for d in dxs if d > 50]
            
        if len(valid_dxs) > 0:
            hist, bin_edges = np.histogram(valid_dxs, bins=15)
            dominant_bin = np.argmax(hist)
            median_w = (bin_edges[dominant_bin] + bin_edges[dominant_bin + 1]) / 2.0
        else:
            median_w = 150.0
            
        # 1D RANSAC fit
        best_anchor = xs[0]
        best_inliers = []
        best_score = 0
        tolerance = 0.15 * median_w
        
        for candidate_anchor in xs:
            inliers = []
            for x in xs:
                diff = (x - candidate_anchor) % median_w
                if diff > 0.5 * median_w:
                    diff = median_w - diff
                if diff <= tolerance:
                    inliers.append(x)
            if len(inliers) > best_score:
                best_score = len(inliers)
                best_anchor = candidate_anchor
                best_inliers = inliers
                
        # Refine anchor using sub-pixel average of inliers
        shifted_inliers = []
        for x in best_inliers:
            k = round((x - best_anchor) / median_w)
            shifted_inliers.append(x - k * median_w)
        best_anchor = np.mean(shifted_inliers)
        
        # Generate perfect grid lines
        min_x = min(xs)
        max_x = max(xs)
        k_min = int(np.floor((min_x - best_anchor) / median_w))
        k_max = int(np.ceil((max_x - best_anchor) / median_w))
        
        grid_xs = [int(best_anchor + k * median_w) for k in range(k_min, k_max + 1)]
        
        # Draw blue grid divider lines
        for x in grid_xs:
            cv2.line(debug_img, (x, row_y_start), (x, row_y_end), (255, 0, 0), 2)
            
        # Generate ROIs between adjacent grid dividers
        for i in range(len(grid_xs) - 1):
            x_left = grid_xs[i]
            x_right = grid_xs[i+1]
            w_slot = x_right - x_left
            
            # Sub-bounding boxes with 8% horizontal and 5% vertical inset padding
            pad_x = int(w_slot * 0.08)
            pad_y = int(row_h * 0.05)
            
            rx = x_left + pad_x
            ry = row_y_start + pad_y
            rw = w_slot - 2 * pad_x
            rh = row_h - 2 * pad_y
            
            # Geometry validation rules
            area = rw * rh
            aspect_ratio = float(rh) / rw if rw > 0 else 0
            
            # Check aspect ratio (typical slot aspect ratio is 1.0 to 4.5)
            # Area must be reasonable (avoid tiny noise or massive overlaps)
            if area > 1500 and area < 0.1 * image_area and 1.0 <= aspect_ratio <= 4.5:
                rois.append({
                    "x": int(rx),
                    "y": int(ry),
                    "width": int(rw),
                    "height": int(rh),
                    "is_ev": False
                })
                # Draw the final generated slot in row color
                cv2.rectangle(debug_img, (rx, ry), (rx + rw, ry + rh), color, 2)
                
    # ------------------ STEP 7: NON-MAX SUPPRESSION & FALLBACK CHECK ------------------
    final_rois = apply_nms(rois, iou_threshold=0.3)
    
    # Save the overlay debug image
    cv2.imwrite(debug_path, debug_img)
    print(f"[Calibration] Saved debugging visual overlays to {debug_path}")
    
    if len(final_rois) < 3:
        return run_yolo_fallback(image, image_path)
        
    return final_rois

def warp_perspective_lot(image_path: str, src_pts: list) -> np.ndarray:
    """
    Warp an angled image of a parking lot to top-down view using Homography transformation.
    """
    img = cv2.imread(image_path)
    if img is None or len(src_pts) != 4:
        return img
        
    pts1 = np.float32(src_pts)
    
    width = int(max(
        np.linalg.norm(pts1[0] - pts1[1]),
        np.linalg.norm(pts1[2] - pts1[3])
    ))
    height = int(max(
        np.linalg.norm(pts1[0] - pts1[3]),
        np.linalg.norm(pts1[1] - pts1[2])
    ))
    
    pts2 = np.float32([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ])
    
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    warped = cv2.warpPerspective(img, matrix, (width, height))
    return warped
