"""
VisionOS AI - Smoothing & Filtering Utilities
"""

import numpy as np
from collections import deque
from typing import Tuple, Optional


class KalmanFilter1D:
    """Simple 1D Kalman filter for smooth cursor tracking."""

    def __init__(self, process_noise=1e-3, measurement_noise=1e-1):
        self.Q = process_noise
        self.R = measurement_noise
        self.P = 1.0
        self.x = None
        self.K = 0.0

    def update(self, measurement: float) -> float:
        if self.x is None:
            self.x = measurement
            return measurement
        # Predict
        self.P += self.Q
        # Update
        self.K = self.P / (self.P + self.R)
        self.x += self.K * (measurement - self.x)
        self.P *= (1 - self.K)
        return self.x

    def reset(self):
        self.x = None
        self.P = 1.0


class CursorSmoother:
    """Smooth XY cursor positions using Kalman + velocity damping."""

    def __init__(self, smoothing_factor: float = 0.7):
        self.kx = KalmanFilter1D()
        self.ky = KalmanFilter1D()
        self.smoothing = smoothing_factor  # 0=no smooth, 1=max
        self.last_x: float = None
        self.last_y: float = None

    def smooth(self, x: float, y: float) -> Tuple[float, float]:
        sx = self.kx.update(x)
        sy = self.ky.update(y)

        if self.last_x is None:
            self.last_x, self.last_y = sx, sy

        # Exponential smoothing on top
        fx = self.last_x + (1 - self.smoothing) * (sx - self.last_x)
        fy = self.last_y + (1 - self.smoothing) * (sy - self.last_y)

        self.last_x, self.last_y = fx, fy
        return fx, fy

    def reset(self):
        self.kx.reset()
        self.ky.reset()
        self.last_x = None
        self.last_y = None


class GestureBuffer:
    """Rolling window for gesture stability detection."""

    def __init__(self, window: int = 5):
        self._buf = deque(maxlen=window)

    def add(self, gesture: str):
        self._buf.append(gesture)

    def dominant(self, threshold: float = 0.6) -> str:
        if not self._buf:
            return "none"
        from collections import Counter
        counts = Counter(self._buf)
        top_gesture, top_count = counts.most_common(1)[0]
        if top_count / len(self._buf) >= threshold:
            return top_gesture
        return "none"

    def clear(self):
        self._buf.clear()


class EyeSmoother:
    """
    Exponential moving average smoother for eye gaze.
    alpha=0.4 balances responsiveness vs jitter suppression.
    Higher alpha (e.g. 0.6) = more responsive but jitterier.
    Lower alpha (e.g. 0.2) = smoother but more lag.
    """

    def __init__(self, window: int = 8, alpha: float = 0.4):
        # window param kept for API compatibility
        self._alpha = alpha
        self._sx: Optional[float] = None
        self._sy: Optional[float] = None

    def smooth(self, x: float, y: float) -> Tuple[float, float]:
        if self._sx is None:
            self._sx, self._sy = float(x), float(y)
        else:
            self._sx = self._alpha * x + (1 - self._alpha) * self._sx
            self._sy = self._alpha * y + (1 - self._alpha) * self._sy
        return self._sx, self._sy

    def reset(self):
        self._sx = None
        self._sy = None
