"""
VisionOS AI - Hand Gesture Detector
Uses MediaPipe Hands to detect and classify gestures
"""

import numpy as np
import time
import math
from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

# Gesture names
GESTURE_NONE = "none"
GESTURE_POINT = "point"           # Index finger → move cursor
GESTURE_PINCH = "pinch"           # Thumb+Index → left click
GESTURE_TWO_PINCH = "two_pinch"   # Index+Middle → right click
GESTURE_DOUBLE_PINCH = "double_pinch"  # double pinch → double click
GESTURE_FIST = "fist"             # Closed fist → drag
GESTURE_OPEN_PALM = "open_palm"   # Open palm → pause
GESTURE_SWIPE_RIGHT = "swipe_right"
GESTURE_SWIPE_LEFT = "swipe_left"
GESTURE_THUMBS_UP = "thumbs_up"
GESTURE_THUMBS_DOWN = "thumbs_down"
GESTURE_SCROLL_UP = "scroll_up"
GESTURE_SCROLL_DOWN = "scroll_down"


class HandDetector:
    """
    Detects hand landmarks and classifies gestures using MediaPipe.
    Designed to run in a background thread.
    """

    def __init__(self, max_hands: int = 1, detection_confidence: float = 0.7,
                 tracking_confidence: float = 0.7):
        self._mp = None
        self._hands = None
        self._max_hands = max_hands
        self._det_conf = detection_confidence
        self._trk_conf = tracking_confidence
        self._initialized = False

        # Swipe tracking
        self._swipe_history: List[float] = []
        self._swipe_time: float = 0.0
        self._swipe_window = 0.6  # seconds

        # Double-pinch tracking
        self._last_pinch_time = 0.0
        self._double_pinch_threshold = 0.45

        # Landmark indices (MediaPipe Hand)
        self.WRIST = 0
        self.THUMB_TIP = 4; self.THUMB_MCP = 2
        self.INDEX_TIP = 8; self.INDEX_MCP = 5; self.INDEX_PIP = 6
        self.MIDDLE_TIP = 12; self.MIDDLE_MCP = 9; self.MIDDLE_PIP = 10
        self.RING_TIP = 16; self.RING_MCP = 13
        self.PINKY_TIP = 20; self.PINKY_MCP = 17

    def initialize(self) -> bool:
        try:
            import mediapipe as mp
            self._mp = mp
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=self._max_hands,
                min_detection_confidence=self._det_conf,
                min_tracking_confidence=self._trk_conf,
                model_complexity=0  # fastest
            )
            self._initialized = True
            logger.info("HandDetector initialized")
            return True
        except Exception as e:
            logger.error(f"HandDetector init failed: {e}")
            return False

    def release(self):
        if self._hands:
            self._hands.close()
            self._initialized = False

    def process_frame(self, frame_rgb: np.ndarray) -> Dict:
        """
        Process an RGB frame and return detection results.
        Returns dict: {detected, landmarks, gesture, cursor_pos, confidence}
        """
        result = {
            "detected": False,
            "landmarks": [],
            "gesture": GESTURE_NONE,
            "cursor_pos": None,
            "confidence": 0.0,
            "hand_label": "Unknown"
        }

        if not self._initialized or self._hands is None:
            return result

        try:
            h, w = frame_rgb.shape[:2]
            mp_result = self._hands.process(frame_rgb)

            if not mp_result.multi_hand_landmarks:
                return result

            hand_landmarks = mp_result.multi_hand_landmarks[0]
            lm = hand_landmarks.landmark

            result["detected"] = True
            result["landmarks"] = lm

            # Hand label
            if mp_result.multi_handedness:
                result["hand_label"] = mp_result.multi_handedness[0].classification[0].label
                result["confidence"] = mp_result.multi_handedness[0].classification[0].score

            # Cursor position = index fingertip (normalized)
            idx_tip = lm[self.INDEX_TIP]
            result["cursor_pos"] = (idx_tip.x, idx_tip.y)

            # Classify gesture
            gesture = self._classify_gesture(lm, w, h)
            result["gesture"] = gesture

        except Exception as e:
            logger.debug(f"process_frame error: {e}")

        return result

    def _dist(self, a, b) -> float:
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    def _finger_up(self, lm, tip_idx: int, pip_idx: int) -> bool:
        """Returns True if finger is extended (tip above pip in image coords)."""
        return lm[tip_idx].y < lm[pip_idx].y

    def _classify_gesture(self, lm, w: int, h: int) -> str:
        thumb_up = lm[self.THUMB_TIP].y < lm[self.THUMB_MCP].y
        index_up = self._finger_up(lm, self.INDEX_TIP, self.INDEX_PIP)
        middle_up = self._finger_up(lm, self.MIDDLE_TIP, self.MIDDLE_PIP)
        ring_up = self._finger_up(lm, self.RING_TIP, self.RING_MCP)
        pinky_up = self._finger_up(lm, self.PINKY_TIP, self.PINKY_MCP)

        fingers_up = [index_up, middle_up, ring_up, pinky_up]
        up_count = sum(fingers_up)

        # Pinch distances
        thumb_index_dist = self._dist(lm[self.THUMB_TIP], lm[self.INDEX_TIP])
        thumb_middle_dist = self._dist(lm[self.THUMB_TIP], lm[self.MIDDLE_TIP])
        index_middle_dist = self._dist(lm[self.INDEX_TIP], lm[self.MIDDLE_TIP])

        PINCH_THRESH = 0.05
        pinch_ti = thumb_index_dist < PINCH_THRESH
        pinch_tm = thumb_middle_dist < PINCH_THRESH
        pinch_im = index_middle_dist < PINCH_THRESH

        # Open palm - all fingers up
        if up_count >= 4 and not pinch_ti:
            return GESTURE_OPEN_PALM

        # Fist - all fingers down
        if up_count == 0 and not thumb_up:
            return GESTURE_FIST

        # Thumbs up - only thumb extended, pointing up
        if thumb_up and up_count == 0:
            if lm[self.THUMB_TIP].y < lm[self.WRIST].y - 0.1:
                return GESTURE_THUMBS_UP

        # Thumbs down - only thumb extended, pointing down
        if not thumb_up and up_count == 0:
            if lm[self.THUMB_TIP].y > lm[self.WRIST].y + 0.05:
                return GESTURE_THUMBS_DOWN

        # Scroll gestures: index + middle up, hand moving vertically
        if index_up and middle_up and not ring_up and not pinky_up:
            return GESTURE_SCROLL_UP  # Will be refined by motion in engine

        # Double pinch detection
        if pinch_ti and index_up:
            now = time.time()
            if now - self._last_pinch_time < self._double_pinch_threshold:
                self._last_pinch_time = 0  # reset
                return GESTURE_DOUBLE_PINCH
            self._last_pinch_time = now
            return GESTURE_PINCH

        # Right click: index+middle pinch
        if pinch_im and not ring_up:
            return GESTURE_TWO_PINCH

        # Swipe detection: open palm moving fast
        if index_up and not middle_up:
            self._update_swipe(lm[self.INDEX_TIP].x)
            swipe = self._detect_swipe()
            if swipe:
                return swipe

        # Default: point with index
        if index_up and not middle_up and not ring_up:
            return GESTURE_POINT

        return GESTURE_NONE

    def _update_swipe(self, x: float):
        now = time.time()
        if now - self._swipe_time > self._swipe_window:
            self._swipe_history = []
        self._swipe_history.append(x)
        self._swipe_time = now

    def _detect_swipe(self) -> Optional[str]:
        if len(self._swipe_history) < 5:
            return None
        dx = self._swipe_history[-1] - self._swipe_history[0]
        if abs(dx) > 0.25:
            self._swipe_history = []
            return GESTURE_SWIPE_RIGHT if dx > 0 else GESTURE_SWIPE_LEFT
        return None

    def draw_landmarks(self, frame_bgr: np.ndarray, landmarks) -> np.ndarray:
        """Draw hand landmarks on frame (for debug view)."""
        try:
            import mediapipe as mp
            import cv2
            mp_drawing = mp.solutions.drawing_utils
            mp_hands = mp.solutions.hands
            # Wrap landmarks in a result-like structure
            class FakeLM:
                def __init__(self, lm):
                    self.landmark = lm
            mp_drawing.draw_landmarks(
                frame_bgr,
                FakeLM(landmarks),
                mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 150), thickness=2, circle_radius=3),
                mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=2)
            )
        except Exception as e:
            logger.debug(f"draw_landmarks error: {e}")
        return frame_bgr
