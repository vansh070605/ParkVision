import asyncio
import cv2
import base64
import logging
from typing import Set

class FrameBroadcaster:
    def __init__(self):
        self.listeners: Set[asyncio.Queue] = set()
        self.loop = asyncio.get_event_loop()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=10)
        self.listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.listeners:
            self.listeners.remove(queue)

    def broadcast(self, frame, metrics: dict):
        """
        Broadcasts raw numpy frame and metrics to all listeners by encoding it to base64.
        This is thread-safe and non-blocking for inference thread.
        """
        if not self.listeners:
            return
            
        try:
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                return
                
            frame_bytes = buffer.tobytes()
            # To allow both WebSocket (base64) and MJPEG (bytes) streams, we generate both or do it on-demand.
            # Base64 is used in WebSocket endpoint
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
            
            payload = {
                "frame": frame_base64,
                "raw_bytes": frame_bytes,
                "metrics": metrics
            }
            
            # Put in queue in thread-safe manner
            for queue in list(self.listeners):
                try:
                    self.loop.call_soon_threadsafe(queue.put_nowait, payload)
                except asyncio.QueueFull:
                    # Drop frame if listener queue is full (slow consumer)
                    try:
                        queue.get_nowait()
                        self.loop.call_soon_threadsafe(queue.put_nowait, payload)
                    except:
                        pass
        except Exception as e:
            logging.error(f"[Broadcaster] Error broadcasting frame: {e}")

# Global broadcaster instance
broadcaster = FrameBroadcaster()
