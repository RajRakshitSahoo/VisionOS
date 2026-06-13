"""
VisionOS AI - Adaptive AI Controller
Automatically selects best control mode based on what's visible
"""

import time
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

MODE_HAND = "hand"
MODE_EYE = "eye"
MODE_HYBRID = "hybrid"
MODE_ADAPTIVE = "adaptive"
MODE_NONE = "none"


class AdaptiveController:
    """
    Monitors hand and eye detection states and decides which control
    mode should be active. Emits mode-change events.
    """

    def __init__(self):
        self._hand_detected = False
        self._eye_detected = False
        self._active_mode = MODE_NONE
        self._last_mode_change = 0.0
        self._mode_stable_duration = 1.5  # seconds before switching mode
        self._pending_mode = MODE_NONE
        self._pending_since = 0.0

        self.on_mode_change: Optional[Callable[[str], None]] = None

    def update(self, hand_detected: bool, eye_detected: bool):
        """Called each frame to update detection state."""
        self._hand_detected = hand_detected
        self._eye_detected = eye_detected

        desired = self._compute_desired_mode()

        if desired != self._active_mode:
            now = time.time()
            if desired != self._pending_mode:
                self._pending_mode = desired
                self._pending_since = now
            elif now - self._pending_since >= self._mode_stable_duration:
                self._switch_mode(desired)
        else:
            self._pending_mode = self._active_mode

    def _compute_desired_mode(self) -> str:
        if self._hand_detected and self._eye_detected:
            return MODE_HYBRID
        elif self._hand_detected:
            return MODE_HAND
        elif self._eye_detected:
            return MODE_EYE
        return MODE_NONE

    def _switch_mode(self, new_mode: str):
        old = self._active_mode
        self._active_mode = new_mode
        self._last_mode_change = time.time()
        logger.info(f"Adaptive mode: {old} → {new_mode}")
        if self.on_mode_change:
            self.on_mode_change(new_mode)

    @property
    def active_mode(self) -> str:
        return self._active_mode

    def get_status_text(self) -> str:
        icons = {
            MODE_HAND: "🖐 Hand Mode",
            MODE_EYE: "👁 Eye Mode",
            MODE_HYBRID: "🤝 Hybrid Mode",
            MODE_NONE: "⚠ No Input Detected"
        }
        return icons.get(self._active_mode, "Unknown")


class IntentPredictor:
    """
    Lightweight AI intent prediction based on usage history.
    Suggests apps based on frequency + time of day.
    """

    def __init__(self, profile_id: int):
        self._profile_id = profile_id
        self._suggestion: Optional[dict] = None
        self._last_check = 0.0
        self._check_interval = 30.0  # check every 30s

    def tick(self) -> Optional[dict]:
        """Returns a suggestion dict if one is ready, else None."""
        now = time.time()
        if now - self._last_check < self._check_interval:
            return None
        self._last_check = now
        return self._compute_suggestion()

    def _compute_suggestion(self) -> Optional[dict]:
        try:
            from database.db_manager import get_frequent_apps
            apps = get_frequent_apps(self._profile_id, limit=3)
            if apps:
                top = apps[0]
                return {
                    "app_name": top[0],
                    "app_path": top[1],
                    "open_count": top[2],
                    "message": f"Open {top[0]}? (used {top[2]}x)"
                }
        except Exception as e:
            logger.debug(f"IntentPredictor error: {e}")
        return None
