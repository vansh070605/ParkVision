import time
import numpy as np

class Track:
    def __init__(self, track_id: int, bbox: tuple, timestamp: float):
        self.track_id = track_id
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.start_time = timestamp
        self.last_active = timestamp
        self.trajectory = [self.get_centroid()]
        self.current_spot_id = None
        self.spot_entered_time = None

    def get_centroid(self):
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def update(self, bbox: tuple, timestamp: float):
        self.bbox = bbox
        self.last_active = timestamp
        self.trajectory.append(self.get_centroid())
        # Keep trajectory length reasonable
        if len(self.trajectory) > 100:
            self.trajectory.pop(0)

class IoUTracker:
    def __init__(self, max_lost_frames: int = 10, iou_threshold: float = 0.3):
        self.max_lost_frames = max_lost_frames
        self.iou_threshold = iou_threshold
        self.next_track_id = 1
        self.tracks = {}  # track_id -> Track

    def _compute_iou(self, box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0

    def update(self, detections: list) -> list:
        """
        detections: List of bboxes (x1, y1, x2, y2)
        Returns: List of active tracks with (track_id, bbox, centroid)
        """
        now = time.time()
        
        # Match detections to existing tracks
        track_ids = list(self.tracks.keys())
        detection_indices = list(range(len(detections)))
        
        matched_detections = {} # detection_idx -> track_id
        
        if track_ids and detection_indices:
            # Build IoU cost matrix
            cost_matrix = np.zeros((len(track_ids), len(detections)))
            for i, tid in enumerate(track_ids):
                for j, det in enumerate(detections):
                    cost_matrix[i, j] = self._compute_iou(self.tracks[tid].bbox, det)
            
            # Simple greedy matching
            while True:
                max_val = np.max(cost_matrix)
                if max_val < self.iou_threshold:
                    break
                
                # Get the indexes of max IoU
                i, j = np.unravel_index(np.argmax(cost_matrix), cost_matrix.shape)
                tid = track_ids[i]
                
                matched_detections[j] = tid
                cost_matrix[i, :] = -1 # Prevent this track from matching again
                cost_matrix[:, j] = -1 # Prevent this detection from matching again
                
        # Update matched tracks
        for det_idx, tid in matched_detections.items():
            self.tracks[tid].update(detections[det_idx], now)
            
        # Register unmatched detections as new tracks
        for j in detection_indices:
            if j not in matched_detections:
                self.tracks[self.next_track_id] = Track(self.next_track_id, detections[j], now)
                self.next_track_id += 1
                
        # Clean up old lost tracks
        lost_tids = []
        for tid, track in self.tracks.items():
            if now - track.last_active > self.max_lost_frames * 0.1: # approx 10 frames at 100ms per frame
                lost_tids.append(tid)
                
        for tid in lost_tids:
            del self.tracks[tid]
            
        # Return currently active tracks
        active_tracks = []
        for tid, track in self.tracks.items():
            if track.last_active == now:
                active_tracks.append({
                    "track_id": tid,
                    "bbox": track.bbox,
                    "centroid": track.get_centroid()
                })
        return active_tracks
