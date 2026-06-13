"""
VisionOS AI - Vision Engine
Orchestrates camera, hand detection, eye detection in background threads
"""

import cv2
import threading
import time
import numpy as np
from typing import Optional, Callable, Dict
import logging

from .camera_thread import CameraThread
from gesture_engine.hand_detector import HandDetector
from gesture_engine.gesture_controller import GestureController
from eye_tracking.eye_detector import EyeDetector
from eye_tracking.eye_controller import EyeController
from adaptive_ai.adaptive_controller import (
    AdaptiveController, IntentPredictor,
    MODE_HAND, MODE_EYE, MODE_HYBRID, MODE_ADAPTIVE, MODE_NONE
)

logger = logging.getLogger(__name__)


class VisionEngine:
    """
    Main engine that runs camera + detection + control in background threads.
    Provides callbacks for UI updates.
    """

    def __init__(self, mode: str, screen_w: int, screen_h: int,
                 profile_id: int = 1, settings: dict = None):
        self._mode = mode
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._profile_id = profile_id
        self._settings = settings or {}

        # Camera
        cam_idx = self._settings.get("camera_index", 0)
        self._camera = CameraThread(
            camera_index=cam_idx, width=640, height=480, fps_limit=30
        )
        self._camera.on_error = self._on_camera_error

        # Detectors
        self._hand_detector = HandDetector(
            detection_confidence=self._settings.get("hand_conf", 0.7),
            tracking_confidence=self._settings.get("hand_track_conf", 0.7)
        )
        self._eye_detector = EyeDetector(
            detection_confidence=self._settings.get("eye_conf", 0.7),
            tracking_confidence=self._settings.get("eye_track_conf", 0.7)
        )

        # Controllers
        self._gesture_ctrl = GestureController(screen_w, screen_h, self._settings)
        self._eye_ctrl = EyeController(screen_w, screen_h, self._settings)

        # Adaptive AI
        self._adaptive = AdaptiveController()
        self._intent = IntentPredictor(profile_id)

        # State
        self._running = False
        self._process_thread: Optional[threading.Thread] = None
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._active_mode = mode

        # Calibration
        if mode == MODE_EYE or mode == MODE_HYBRID or mode == MODE_ADAPTIVE:
            from database.db_manager import get_calibration
            calib = get_calibration(profile_id, "eye")
            if calib:
                self._eye_detector.set_calibration(calib)

        # Callbacks
        self.on_frame: Optional[Callable[[np.ndarray], None]] = None
        self.on_status: Optional[Callable[[Dict], None]] = None
        self.on_notify: Optional[Callable[[str], None]] = None
        self.on_suggestion: Optional[Callable[[Dict], None]] = None

        # Wire notification callbacks
        self._gesture_ctrl.on_notify = self._handle_notify
        self._eye_ctrl.on_notify = self._handle_notify
        self._adaptive.on_mode_change = self._on_adaptive_mode_change

    def start(self):
        """Start camera and processing threads."""
        if self._running:
            return

        # Init detectors based on mode
        needs_hand = self._mode in (MODE_HAND, MODE_HYBRID, MODE_ADAPTIVE)
        needs_eye = self._mode in (MODE_EYE, MODE_HYBRID, MODE_ADAPTIVE)

        if needs_hand:
            ok = self._hand_detector.initialize()
            if not ok:
                self._handle_notify("⚠ Hand detector init failed")

        if needs_eye:
            ok = self._eye_detector.initialize()
            if not ok:
                self._handle_notify("⚠ Eye detector init failed")

        self._camera.start()
        self._running = True
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()
        logger.info(f"VisionEngine started (mode={self._mode})")

    def stop(self):
        """Stop all threads and release resources."""
        self._running = False
        self._camera.stop()
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
        self._hand_detector.release()
        self._eye_detector.release()
        logger.info("VisionEngine stopped")

    def _process_loop(self):
        """Main processing loop running in background thread."""
        while self._running:
            frame = self._camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]

            hand_detected = False
            eye_detected = False

            # Determine active mode
            if self._mode == MODE_ADAPTIVE:
                active = self._adaptive.active_mode or MODE_NONE
            else:
                active = self._mode

            # Hand processing
            hand_result = {"detected": False, "gesture": "none", "confidence": 0.0}
            if active in (MODE_HAND, MODE_HYBRID) or self._mode == MODE_ADAPTIVE:
                hand_result = self._hand_detector.process_frame(frame_rgb)
                hand_detected = hand_result["detected"]

                if active == MODE_HAND and hand_detected:
                    self._gesture_ctrl.process(hand_result, h, w)
                elif active == MODE_HYBRID and hand_detected:
                    # In hybrid: hand confirms, eye targets
                    self._gesture_ctrl.process(hand_result, h, w)

            # Eye processing
            eye_result = {"detected": False, "blink": "none", "ear": 1.0, "gaze_norm": (0.5, 0.5)}
            if active in (MODE_EYE, MODE_HYBRID) or self._mode == MODE_ADAPTIVE:
                eye_result = self._eye_detector.process_frame(frame_rgb)
                eye_detected = eye_result["detected"]

                if active == MODE_EYE and eye_detected:
                    self._eye_ctrl.process(eye_result, self._eye_detector)
                elif active == MODE_HYBRID and eye_detected:
                    # In hybrid: eye moves cursor
                    self._eye_ctrl.process(eye_result, self._eye_detector)

            # Adaptive mode update
            if self._mode == MODE_ADAPTIVE:
                self._adaptive.update(hand_detected, eye_detected)
                if hand_detected:
                    self._gesture_ctrl.process(hand_result, h, w)
                elif eye_detected:
                    self._eye_ctrl.process(eye_result, self._eye_detector)

            # Draw overlays
            display = frame.copy()
            if hand_result["detected"] and hand_result.get("landmarks"):
                self._hand_detector.draw_landmarks(display, hand_result["landmarks"])
            if eye_result["detected"] and eye_result.get("face_landmarks"):
                self._eye_detector.draw_landmarks(display, eye_result["face_landmarks"])

            with self._frame_lock:
                self._current_frame = display

            # Emit frame callback
            if self.on_frame:
                self.on_frame(display)

            # Emit status
            if self.on_status:
                self.on_status({
                    "fps": self._camera.get_fps(),
                    "mode": self._adaptive.active_mode if self._mode == MODE_ADAPTIVE else self._mode,
                    "hand_detected": hand_detected,
                    "eye_detected": eye_detected,
                    "gesture": hand_result.get("gesture", "none"),
                    "ear": eye_result.get("ear", 1.0),
                    "confidence": hand_result.get("confidence", 0.0),
                })

            # Intent prediction
            suggestion = self._intent.tick()
            if suggestion and self.on_suggestion:
                self.on_suggestion(suggestion)

    def get_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
        return None

    def _handle_notify(self, msg: str):
        if self.on_notify:
            self.on_notify(msg)

    def _on_adaptive_mode_change(self, new_mode: str):
        self._active_mode = new_mode
        self._handle_notify(f"🔄 Mode: {new_mode.upper()}")

    def _on_camera_error(self, msg: str):
        self._handle_notify(f"📷 Camera: {msg}")

    @property
    def active_mode(self) -> str:
        if self._mode == MODE_ADAPTIVE:
            return self._adaptive.active_mode
        return self._mode

    def update_settings(self, settings: dict):
        self._settings.update(settings)
        self._gesture_ctrl.update_settings(settings)
        self._eye_ctrl.update_settings(settings)
