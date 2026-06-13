"""
VisionOS AI - Eye Tracking Detector
Uses MediaPipe Face Mesh for gaze estimation and blink detection
"""

import numpy as np
import math
import time
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# MediaPipe Face Mesh landmark indices for eyes
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

# Iris landmarks
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

# EAR threshold
EAR_BLINK_THRESHOLD = 0.21
EAR_LONG_BLINK_THRESHOLD = 0.18

BLINK_NONE = "none"
BLINK_SINGLE = "single"
BLINK_DOUBLE = "double"
BLINK_LONG = "long"


class EyeDetector:
    """
    Detects eye gaze direction and blink patterns using MediaPipe Face Mesh.
    """

    def __init__(self, detection_confidence: float = 0.7, tracking_confidence: float = 0.7):
        self._det_conf = detection_confidence
        self._trk_conf = tracking_confidence
        self._face_mesh = None
        self._initialized = False

        # Blink tracking
        self._blink_history: List[Tuple[float, str]] = []  # (time, "open"/"closed")
        self._last_ear: float = 1.0
        self._eye_closed_start: float = 0.0
        self._eye_is_closed: bool = False
        self._blink_times: List[float] = []
        self._double_blink_window = 0.5
        self._long_blink_duration = 0.4

        # Gaze
        self._calibration: Dict = {}
        self._is_calibrated = False

    def initialize(self) -> bool:
        try:
            import mediapipe as mp
            self._mp = mp
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,  # enables iris landmarks
                min_detection_confidence=self._det_conf,
                min_tracking_confidence=self._trk_conf
            )
            self._initialized = True
            logger.info("EyeDetector initialized")
            return True
        except Exception as e:
            logger.error(f"EyeDetector init failed: {e}")
            return False

    def release(self):
        if self._face_mesh:
            self._face_mesh.close()
            self._initialized = False

    def process_frame(self, frame_rgb: np.ndarray) -> Dict:
        """
        Process RGB frame. Returns:
        {detected, gaze_norm, blink, ear, face_landmarks}
        """
        result = {
            "detected": False,
            "gaze_norm": (0.5, 0.5),
            "blink": BLINK_NONE,
            "ear": 1.0,
            "face_landmarks": None
        }

        if not self._initialized:
            return result

        try:
            h, w = frame_rgb.shape[:2]
            mp_result = self._face_mesh.process(frame_rgb)

            if not mp_result.multi_face_landmarks:
                return result

            face_lm = mp_result.multi_face_landmarks[0].landmark
            result["detected"] = True
            result["face_landmarks"] = face_lm

            # --- EAR for blink detection ---
            left_ear = self._eye_aspect_ratio(face_lm, LEFT_EYE)
            right_ear = self._eye_aspect_ratio(face_lm, RIGHT_EYE)
            avg_ear = (left_ear + right_ear) / 2.0
            result["ear"] = avg_ear

            # Blink detection
            blink_event = self._detect_blink(avg_ear)
            result["blink"] = blink_event

            # --- Iris-based gaze ---
            gaze = self._estimate_gaze(face_lm, w, h)
            result["gaze_norm"] = gaze

        except Exception as e:
            logger.debug(f"EyeDetector process_frame error: {e}")

        return result

    def _eye_aspect_ratio(self, lm, eye_indices: List[int]) -> float:
        """Calculate Eye Aspect Ratio (EAR)."""
        # Use a subset: vertical pairs and horizontal pair
        # Simplified EAR: use top/bottom distances vs width
        try:
            pts = [(lm[i].x, lm[i].y) for i in eye_indices]

            # Horizontal: first and 8th point
            h_dist = math.sqrt((pts[0][0] - pts[8][0])**2 + (pts[0][1] - pts[8][1])**2)
            if h_dist < 1e-6:
                return 0.3

            # Vertical: average of two pairs
            v1 = math.sqrt((pts[2][0] - pts[14][0])**2 + (pts[2][1] - pts[14][1])**2)
            v2 = math.sqrt((pts[4][0] - pts[12][0])**2 + (pts[4][1] - pts[12][1])**2)
            ear = (v1 + v2) / (2.0 * h_dist)
            return ear
        except Exception:
            return 0.3

    def _detect_blink(self, ear: float) -> str:
        now = time.time()

        if ear < EAR_BLINK_THRESHOLD:
            if not self._eye_is_closed:
                self._eye_is_closed = True
                self._eye_closed_start = now
        else:
            if self._eye_is_closed:
                closed_duration = now - self._eye_closed_start
                self._eye_is_closed = False

                if closed_duration >= self._long_blink_duration:
                    return BLINK_LONG

                # Record blink time for double-blink detection
                self._blink_times.append(now)
                # Remove old blinks outside window
                self._blink_times = [t for t in self._blink_times
                                     if now - t <= self._double_blink_window]

                if len(self._blink_times) >= 2:
                    self._blink_times.clear()
                    return BLINK_DOUBLE

                return BLINK_SINGLE

        return BLINK_NONE

    def _estimate_gaze(self, lm, w: int, h: int) -> Tuple[float, float]:
        """
        Estimate normalized gaze position (0..1, 0..1) using iris position
        relative to eye corners. Uses BOTH eyes averaged for stability.
        """
        try:
            # Average both irises for more stable gaze estimation
            l_iris = [lm[i] for i in LEFT_IRIS]
            r_iris = [lm[i] for i in RIGHT_IRIS]

            iris_cx = (sum(p.x for p in l_iris) / len(l_iris) +
                       sum(p.x for p in r_iris) / len(r_iris)) / 2.0
            iris_cy = (sum(p.y for p in l_iris) / len(l_iris) +
                       sum(p.y for p in r_iris) / len(r_iris)) / 2.0

            # Eye corners: left eye left-corner and right eye right-corner
            # give us the full horizontal span of both eyes
            left_corner  = lm[LEFT_EYE[8]]   # rightmost point of left eye
            right_corner = lm[RIGHT_EYE[0]]  # leftmost point of right eye
            l_outer = lm[LEFT_EYE[0]]
            r_outer = lm[RIGHT_EYE[8]]

            full_eye_span_x = abs(r_outer.x - l_outer.x)
            if full_eye_span_x < 1e-4:
                return (0.5, 0.5)

            # Vertical: use top/bottom of left eye
            eye_top    = lm[LEFT_EYE[2]].y
            eye_bottom = lm[LEFT_EYE[12]].y
            eye_h = abs(eye_bottom - eye_top)

            # Relative iris position across full face span
            rel_x = (iris_cx - l_outer.x) / full_eye_span_x
            rel_y = (iris_cy - eye_top) / (eye_h + 1e-6)

            # Iris only travels ~30-70% of the eye span horizontally
            # and ~20-80% vertically — remap that to full 0..1 range
            gx = (rel_x - 0.30) / 0.40
            gy = (rel_y - 0.20) / 0.60

            gx = max(0.0, min(1.0, gx))
            gy = max(0.0, min(1.0, gy))

            return (gx, gy)
        except Exception:
            return (0.5, 0.5)

    def set_calibration(self, calib_data: dict):
        """Set calibration points for accurate screen mapping."""
        self._calibration = calib_data
        self._is_calibrated = bool(calib_data)

    def map_gaze_to_screen(self, gaze_norm: Tuple[float, float],
                           screen_w: int, screen_h: int) -> Tuple[int, int]:
        """Map normalized gaze to screen coordinates using calibration."""
        gx, gy = gaze_norm

        if self._is_calibrated and "transform" in self._calibration:
            # Apply affine transform if calibrated
            t = self._calibration["transform"]
            sx = t["ax"] * gx + t["bx"] * gy + t["cx"]
            sy = t["ay"] * gx + t["by"] * gy + t["cy"]
        else:
            # Simple linear mapping (fallback)
            sx = gx * screen_w
            sy = gy * screen_h

        sx = max(0, min(screen_w - 1, int(sx)))
        sy = max(0, min(screen_h - 1, int(sy)))
        return sx, sy

    def draw_landmarks(self, frame_bgr: np.ndarray, face_landmarks,
                       draw_iris: bool = True) -> np.ndarray:
        """Draw eye/iris landmarks on frame."""
        try:
            import cv2
            import mediapipe as mp

            h, w = frame_bgr.shape[:2]
            lm = face_landmarks

            # Draw eye contours
            for idx in LEFT_EYE + RIGHT_EYE:
                pt = lm[idx]
                cx, cy = int(pt.x * w), int(pt.y * h)
                cv2.circle(frame_bgr, (cx, cy), 1, (0, 255, 100), -1)

            # Draw iris
            if draw_iris:
                for idx in LEFT_IRIS + RIGHT_IRIS:
                    pt = lm[idx]
                    cx, cy = int(pt.x * w), int(pt.y * h)
                    cv2.circle(frame_bgr, (cx, cy), 2, (0, 200, 255), -1)

        except Exception as e:
            logger.debug(f"draw_landmarks error: {e}")
        return frame_bgr
