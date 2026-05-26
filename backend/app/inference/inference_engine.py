import os
import cv2
import torch
from ultralytics import YOLO
from app.config.config import settings
from app.models.cnn_classifier import CNNClassifierService

class InferenceEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Inference] Initializing inference engine on device: {self.device}")
        
        # Load YOLO model
        self.yolo_model = self._load_yolo()
        self.yolo_classes = [2, 5, 7, 3] # COCO classes: 2: car, 5: bus, 7: truck, 3: motorcycle
        
        # Load CNN Classifier
        self.cnn_classifier = CNNClassifierService()
        
    def _load_yolo(self) -> YOLO:
        # Check if custom fine-tuned weights exist in the runs folder
        custom_weights_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            settings.CUSTOM_WEIGHTS_DIR,
            "best.pt"
        )
        
        if os.path.exists(custom_weights_path):
            print(f"[Inference] Loading custom YOLOv8 model from {custom_weights_path}")
            model = YOLO(custom_weights_path)
        else:
            print(f"[Inference] Fallback to pre-trained model: {settings.YOLO_MODEL_PATH}")
            model = YOLO(settings.YOLO_MODEL_PATH)
            
        return model

    def run_object_detection(self, frame) -> list:
        """
        Runs YOLOv8 object detection on a single frame.
        Returns list of bboxes: (x1, y1, x2, y2, confidence, class_id)
        """
        # Run YOLO with GPU settings if CUDA is available
        half_precision = (self.device == "cuda")
        results = self.yolo_model(
            frame,
            classes=self.yolo_classes,
            conf=settings.CONFIDENCE_THRESHOLD,
            iou=settings.IOU_THRESHOLD,
            imgsz=settings.STREAM_WIDTH,
            half=half_precision,
            device=self.device,
            verbose=False
        )
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                detections.append((x1, y1, x2, y2, conf, cls_id))
                
        return detections

    def classify_rois(self, frame, rois: list) -> list:
        """
        Extracts crops from frame according to ROIs list and classifies them with CNN.
        rois: list of dicts with keys 'x', 'y', 'width', 'height'
        Returns: list of dicts with 'occupied' and 'confidence'
        """
        if not rois:
            return []
            
        crops = []
        valid_indices = []
        height, width = frame.shape[:2]
        
        for i, roi in enumerate(rois):
            rx, ry, rw, rh = int(roi['x']), int(roi['y']), int(roi['width']), int(roi['height'])
            
            # Constrain bounding boxes to image dimensions
            rx1 = max(0, rx)
            ry1 = max(0, ry)
            rx2 = min(width, rx + rw)
            ry2 = min(height, ry + rh)
            
            if (rx2 - rx1) > 5 and (ry2 - ry1) > 5:
                crop = frame[ry1:ry2, rx1:rx2]
                crops.append(crop)
                valid_indices.append(i)
                
        if not crops:
            return [{"occupied": False, "confidence": 1.0} for _ in rois]
            
        # Get batch predictions from CNN classifier
        predictions = self.cnn_classifier.predict_batch(crops)
        
        # Build full results list matching length of original ROIs
        full_results = []
        pred_idx = 0
        for i in range(len(rois)):
            if i in valid_indices:
                full_results.append(predictions[pred_idx])
                pred_idx += 1
            else:
                full_results.append({"occupied": False, "confidence": 1.0})
                
        return full_results
