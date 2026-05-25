import cv2
import numpy as np
import os

width, height = 640, 480
fps = 30
duration = 10  # seconds
num_frames = fps * duration

filepath = os.path.join(os.path.dirname(__file__), 'sample_video.mp4')
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

for i in range(num_frames):
    frame = np.ones((height, width, 3), dtype=np.uint8) * 50  # dark gray background
    
    # Draw some "cars" that occasionally appear or disappear
    # Spot 1: Empty
    # Spot 2: Occupied always
    cv2.rectangle(frame, (260, 110), (340, 240), (200, 200, 200), -1)
    # Spot 3: Appears halfway
    if i > num_frames // 2:
        cv2.rectangle(frame, (410, 110), (490, 240), (150, 50, 50), -1)
    # Spot 4: Occupied
    cv2.rectangle(frame, (110, 310), (190, 440), (50, 150, 50), -1)
    # Spot 5: Empty
    # Spot 6: Disappears halfway
    if i < num_frames // 2:
        cv2.rectangle(frame, (410, 310), (490, 440), (50, 50, 150), -1)
        
    # Add some noise to simulate video feed
    noise = np.random.normal(0, 10, (height, width, 3)).astype(np.uint8)
    frame = cv2.add(frame, noise)

    out.write(frame)

out.release()
print(f"Created {filepath}")
