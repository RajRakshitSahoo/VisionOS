"""
VisionOS AI - Eye Controller
Maps eye detection results to system actions
"""

import time
from typing import Optional, Callable, Tuple
import logging

from .eye_detector import BLINK_SINGLE, BLINK_DOUBLE, BLINK_LONG, BLINK_NONE
from utils.smoothing import EyeSmoother

logger = logging.getLogger(__name__)


class EyeController:
    """Translates eye gaze + blink events into mouse actions."""

    def __init__(self, screen_w: int, screen_h: int, settings: dict = None):
        self._screen_w = screen_w
        self._screen_h = screen_h
        from utils.system_control import get_controller
        self._sys = get_controller()
        self._smoother = EyeSmoother(window=5, alpha=0.4)

        cfg = settings or {}
        self._dwell_time = cfg.get("dwell_time", 0.8)
        self._click_cooldown = cfg.get("eye_click_cooldown", 0.5)

        # State
        self._last_blink_time = 0.0
        self._last_pos = (screen_w // 2, screen_h // 2)

        self.on_notify: Optional[Callable[[str], None]] = None

    def process(self, detection: dict, eye_detector):
        """Called each frame with EyeDetector output."""
        if not detection["detected"]:
            return

        gaze_norm = detection["gaze_norm"]
        blink = detection["blink"]

        # Map gaze to screen
        sx, sy = eye_detector.map_gaze_to_screen(gaze_norm, self._screen_w, self._screen_h)
        smooth_x, smooth_y = self._smoother.smooth(sx, sy)
        fx, fy = int(smooth_x), int(smooth_y)

        # Move cursor
        self._sys.move_cursor(fx, fy)
        self._last_pos = (fx, fy)

        # Handle blinks
        if blink != BLINK_NONE:
            self._handle_blink(blink, fx, fy)

    def _handle_blink(self, blink: str, x: int, y: int):
        now = time.time()
        if now - self._last_blink_time < self._click_cooldown:
            return
        self._last_blink_time = now

        if blink == BLINK_SINGLE:
            self._sys.left_click(x, y)
            self._notify("👁 Single Blink → Click")

        elif blink == BLINK_DOUBLE:
            self._sys.double_click(x, y)
            self._notify("👁👁 Double Blink → Open")

        elif blink == BLINK_LONG:
            self._sys.right_click(x, y)
            self._notify("👁— Long Blink → Right Click")

    def _notify(self, msg: str):
        if self.on_notify:
            self.on_notify(msg)

    def update_settings(self, settings: dict):
        self._dwell_time = settings.get("dwell_time", self._dwell_time)
        self._click_cooldown = settings.get("eye_click_cooldown", self._click_cooldown)

    def reset(self):
        self._smoother.reset()
        self._last_blink_time = 0.0
