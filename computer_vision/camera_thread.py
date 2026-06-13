"""
VisionOS AI - Camera Thread
Threaded webcam capture with frame queuing for smooth processing
"""

import cv2
import threading
import queue
import time
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CameraThread(threading.Thread):
    """
    Runs webcam capture in a background thread.
    Provides latest frames via get_frame() without blocking.
    """

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480,
                 fps_limit: int = 30):
        super().__init__(daemon=True)
        self._cam_idx = camera_index
        self._width = width
        self._height = height
        self._fps_limit = fps_limit

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        self._running = False
        self._fps = 0.0
        self._frame_count = 0
        self._fps_start = time.time()

        self.on_error: Optional[callable] = None

    def run(self):
        self._running = True
        try:
            self._cap = cv2.VideoCapture(self._cam_idx, cv2.CAP_DSHOW)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            self._cap.set(cv2.CAP_PROP_FPS, self._fps_limit)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self._cap.isOpened():
                logger.error("Cannot open camera")
                if self.on_error:
                    self.on_error("Camera not found")
                return

            min_interval = 1.0 / self._fps_limit

            while self._running:
                t0 = time.time()
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    with self._frame_lock:
                        self._frame = frame
                    self._update_fps()

                elapsed = time.time() - t0
                sleep_t = max(0, min_interval - elapsed)
                if sleep_t > 0:
                    time.sleep(sleep_t)

        except Exception as e:
            logger.error(f"CameraThread error: {e}")
            if self.on_error:
                self.on_error(str(e))
        finally:
            if self._cap:
                self._cap.release()

    def get_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            if self._frame is not None:
                return self._frame.copy()
        return None

    def get_fps(self) -> float:
        return self._fps

    def _update_fps(self):
        self._frame_count += 1
        elapsed = time.time() - self._fps_start
        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_start = time.time()

    def stop(self):
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self.is_alive()

    @staticmethod
    def list_cameras(max_test: int = 5) -> list:
        """Return list of available camera indices."""
        available = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
