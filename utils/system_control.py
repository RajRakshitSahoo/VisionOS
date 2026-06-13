"""
VisionOS AI - System Control Utilities
Cross-platform system actions (Windows-optimized)
All pyautogui calls are lazy to avoid import-time display requirements on Linux.
"""
import sys
import os
import time
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def _pag():
    """Lazy import pyautogui."""
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0
    return pyautogui


class SystemController:
    """Handles all system-level mouse, keyboard, and OS actions."""

    def __init__(self):
        self._drag_active = False
        self._scroll_accumulator = 0.0

    # ── Mouse ───────────────────────────────────────────────
    def move_cursor(self, x: int, y: int):
        try:
            _pag().moveTo(x, y, duration=0)
        except Exception as e:
            logger.debug(f"move_cursor: {e}")

    def left_click(self, x=None, y=None):
        try:
            if x is not None and y is not None:
                _pag().click(x, y)
            else:
                _pag().click()
        except Exception as e:
            logger.debug(f"left_click: {e}")

    def right_click(self, x=None, y=None):
        try:
            if x is not None and y is not None:
                _pag().rightClick(x, y)
            else:
                _pag().rightClick()
        except Exception as e:
            logger.debug(f"right_click: {e}")

    def double_click(self, x=None, y=None):
        try:
            if x is not None and y is not None:
                _pag().doubleClick(x, y)
            else:
                _pag().doubleClick()
        except Exception as e:
            logger.debug(f"double_click: {e}")

    def scroll(self, amount: float):
        try:
            self._scroll_accumulator += amount
            if abs(self._scroll_accumulator) >= 1.0:
                clicks = int(self._scroll_accumulator)
                _pag().scroll(clicks)
                self._scroll_accumulator -= clicks
        except Exception as e:
            logger.debug(f"scroll: {e}")

    def start_drag(self, x: int, y: int):
        try:
            self._drag_active = True
            _pag().mouseDown(x, y)
        except Exception as e:
            logger.debug(f"start_drag: {e}")

    def continue_drag(self, x: int, y: int):
        try:
            if self._drag_active:
                _pag().moveTo(x, y, duration=0)
        except Exception as e:
            logger.debug(f"continue_drag: {e}")

    def end_drag(self, x: int, y: int):
        try:
            if self._drag_active:
                _pag().mouseUp(x, y)
                self._drag_active = False
        except Exception as e:
            logger.debug(f"end_drag: {e}")

    # ── Keyboard ─────────────────────────────────────────────
    def press_key(self, key: str):
        try:
            _pag().press(key)
        except Exception as e:
            logger.debug(f"press_key: {e}")

    def hotkey(self, *keys):
        try:
            _pag().hotkey(*keys)
        except Exception as e:
            logger.debug(f"hotkey: {e}")

    def next_tab(self):
        self.hotkey('ctrl', 'tab')

    def prev_tab(self):
        self.hotkey('ctrl', 'shift', 'tab')

    def switch_window(self):
        self.hotkey('alt', 'tab')

    # ── Volume ───────────────────────────────────────────────
    def increase_volume(self, amount: int = 5):
        try:
            if sys.platform == "win32":
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    current = volume.GetMasterVolumeLevelScalar()
                    volume.SetMasterVolumeLevelScalar(min(1.0, current + amount / 100.0), None)
                    return
                except Exception:
                    pass
            for _ in range(max(1, amount // 2)):
                _pag().press('volumeup')
        except Exception as e:
            logger.debug(f"increase_volume: {e}")

    def decrease_volume(self, amount: int = 5):
        try:
            if sys.platform == "win32":
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    current = volume.GetMasterVolumeLevelScalar()
                    volume.SetMasterVolumeLevelScalar(max(0.0, current - amount / 100.0), None)
                    return
                except Exception:
                    pass
            for _ in range(max(1, amount // 2)):
                _pag().press('volumedown')
        except Exception as e:
            logger.debug(f"decrease_volume: {e}")

    # ── Brightness ───────────────────────────────────────────
    def increase_brightness(self, amount: int = 10):
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness(display=0)
            if isinstance(current, list):
                current = current[0]
            sbc.set_brightness(min(100, current + amount), display=0)
        except Exception as e:
            logger.debug(f"increase_brightness: {e}")

    def decrease_brightness(self, amount: int = 10):
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness(display=0)
            if isinstance(current, list):
                current = current[0]
            sbc.set_brightness(max(0, current - amount), display=0)
        except Exception as e:
            logger.debug(f"decrease_brightness: {e}")

    # ── Apps ─────────────────────────────────────────────────
    def open_application(self, app_path: str):
        try:
            if sys.platform == "win32":
                os.startfile(app_path)
            else:
                import subprocess
                subprocess.Popen([app_path])
        except Exception as e:
            logger.warning(f"open_application '{app_path}': {e}")

    def get_screen_size(self) -> Tuple[int, int]:
        try:
            return _pag().size()
        except Exception:
            return (1920, 1080)

    def get_cursor_pos(self) -> Tuple[int, int]:
        try:
            return _pag().position()
        except Exception:
            return (960, 540)


_controller: Optional[SystemController] = None


def get_controller() -> SystemController:
    global _controller
    if _controller is None:
        _controller = SystemController()
    return _controller
