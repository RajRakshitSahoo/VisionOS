"""
VisionOS AI - Gesture Controller
Maps detected gestures to system actions with debouncing and cooldown
"""

import time
import threading
from typing import Optional, Callable, Dict, Tuple
import logging

from .hand_detector import (
    GESTURE_NONE, GESTURE_POINT, GESTURE_PINCH, GESTURE_TWO_PINCH,
    GESTURE_DOUBLE_PINCH, GESTURE_FIST, GESTURE_OPEN_PALM,
    GESTURE_SWIPE_RIGHT, GESTURE_SWIPE_LEFT, GESTURE_THUMBS_UP,
    GESTURE_THUMBS_DOWN, GESTURE_SCROLL_UP, GESTURE_SCROLL_DOWN
)
from utils.smoothing import CursorSmoother, GestureBuffer

logger = logging.getLogger(__name__)


class GestureController:
    """
    Translates hand gesture detections into system control actions.
    Handles smoothing, cooldowns, drag state, and scroll accumulation.
    """

    def __init__(self, screen_w: int, screen_h: int, settings: dict = None):
        self._screen_w = screen_w
        self._screen_h = screen_h
        from utils.system_control import get_controller
        self._sys = get_controller()
        self._smoother = CursorSmoother(smoothing_factor=0.6)
        self._gesture_buf = GestureBuffer(window=4)

        cfg = settings or {}
        self._cursor_speed = cfg.get("cursor_speed", 1.0)
        self._click_cooldown = cfg.get("click_cooldown", 0.4)

        # State
        self._paused = False
        self._dragging = False
        self._last_gesture = GESTURE_NONE
        self._last_action_time: Dict[str, float] = {}

        # Scroll state
        self._prev_gesture = GESTURE_NONE
        self._scroll_ref_y: Optional[float] = None
        self._scroll_last_y: Optional[float] = None

        # Notification callback
        self.on_notify: Optional[Callable[[str], None]] = None

    def update_settings(self, settings: dict):
        self._cursor_speed = settings.get("cursor_speed", self._cursor_speed)
        self._click_cooldown = settings.get("click_cooldown", self._click_cooldown)
        self._smoother.smoothing = settings.get("smoothing", self._smoother.smoothing)

    def process(self, detection: dict, frame_h: int, frame_w: int):
        """Called every frame with hand detector output."""
        if not detection["detected"]:
            if self._dragging:
                self._end_drag()
            self._gesture_buf.add(GESTURE_NONE)
            return

        raw_gesture = detection["gesture"]
        cursor_norm = detection["cursor_pos"]

        self._gesture_buf.add(raw_gesture)
        stable_gesture = self._gesture_buf.dominant(threshold=0.5)

        # Update cursor position (always, even when doing gestures)
        if cursor_norm:
            self._update_cursor(cursor_norm)

        # Paused by open palm
        if stable_gesture == GESTURE_OPEN_PALM:
            if not self._paused:
                self._paused = True
                self._notify("⏸ Tracking Paused")
            if self._dragging:
                self._end_drag()
            return
        else:
            if self._paused:
                self._paused = False
                self._notify("▶ Tracking Resumed")

        if self._paused:
            return

        # Gesture → action mapping
        self._handle_gesture(stable_gesture, detection)

    def _update_cursor(self, norm_pos: Tuple[float, float]):
        """Map normalized [0,1] camera coords to screen coords with smoothing."""
        # Mirror X (camera is mirrored)
        nx = 1.0 - norm_pos[0]
        ny = norm_pos[1]

        # Clamp with small margin
        nx = max(0.02, min(0.98, nx))
        ny = max(0.02, min(0.98, ny))

        sx = nx * self._screen_w * self._cursor_speed
        sy = ny * self._screen_h * self._cursor_speed

        # Clamp to screen
        sx = max(0, min(self._screen_w - 1, int(sx)))
        sy = max(0, min(self._screen_h - 1, int(sy)))

        smooth_x, smooth_y = self._smoother.smooth(sx, sy)
        smooth_x = max(0, min(self._screen_w - 1, int(smooth_x)))
        smooth_y = max(0, min(self._screen_h - 1, int(smooth_y)))

        if not self._dragging:
            self._sys.move_cursor(smooth_x, smooth_y)
        else:
            self._sys.continue_drag(smooth_x, smooth_y)

    def _handle_gesture(self, gesture: str, detection: dict):
        now = time.time()

        if gesture == GESTURE_PINCH:
            if self._cooldown_ok("click", self._click_cooldown):
                self._sys.left_click()
                self._notify("👆 Left Click")

        elif gesture == GESTURE_DOUBLE_PINCH:
            if self._cooldown_ok("dbl_click", self._click_cooldown):
                self._sys.double_click()
                self._notify("👆👆 Double Click")

        elif gesture == GESTURE_TWO_PINCH:
            if self._cooldown_ok("right_click", self._click_cooldown):
                self._sys.right_click()
                self._notify("👆 Right Click")

        elif gesture == GESTURE_FIST:
            if not self._dragging:
                cx, cy = self._sys.get_cursor_pos()
                self._sys.start_drag(cx, cy)
                self._dragging = True
                self._notify("✊ Drag Started")

        elif gesture == GESTURE_SWIPE_RIGHT:
            if self._cooldown_ok("swipe", 0.5):
                self._sys.next_tab()
                self._notify("→ Next Tab")

        elif gesture == GESTURE_SWIPE_LEFT:
            if self._cooldown_ok("swipe", 0.5):
                self._sys.prev_tab()
                self._notify("← Prev Tab")

        elif gesture == GESTURE_THUMBS_UP:
            if self._cooldown_ok("confirm", 0.8):
                self._sys.press_key("enter")
                self._notify("👍 Confirm")

        elif gesture == GESTURE_THUMBS_DOWN:
            if self._cooldown_ok("cancel", 0.8):
                self._sys.press_key("escape")
                self._notify("👎 Cancel")

        elif gesture == GESTURE_SCROLL_UP:
            self._sys.scroll(2)

        elif gesture == GESTURE_SCROLL_DOWN:
            self._sys.scroll(-2)

        # End drag if gesture changes away from fist
        if self._dragging and gesture != GESTURE_FIST:
            self._end_drag()

        self._last_gesture = gesture

    def _end_drag(self):
        cx, cy = self._sys.get_cursor_pos()
        self._sys.end_drag(cx, cy)
        self._dragging = False
        self._notify("✊ Drag Ended")

    def _cooldown_ok(self, action: str, cooldown: float) -> bool:
        now = time.time()
        last = self._last_action_time.get(action, 0)
        if now - last >= cooldown:
            self._last_action_time[action] = now
            return True
        return False

    def _notify(self, message: str):
        if self.on_notify:
            self.on_notify(message)

    def reset(self):
        self._paused = False
        if self._dragging:
            self._end_drag()
        self._smoother.reset()
        self._gesture_buf.clear()
        self._last_action_time.clear()
