"""
VisionOS AI - Voice Control Engine
Offline voice command recognition (optional module)
Tries Vosk first, then falls back to SpeechRecognition offline
"""

import threading
import queue
import logging
from typing import Callable, Optional, Dict

logger = logging.getLogger(__name__)


VOICE_COMMANDS: Dict[str, str] = {
    "open chrome": "app:chrome",
    "open vs code": "app:vscode",
    "open notepad": "app:notepad",
    "open spotify": "app:spotify",
    "open calculator": "app:calculator",
    "increase volume": "vol:up",
    "decrease volume": "vol:down",
    "volume up": "vol:up",
    "volume down": "vol:down",
    "increase brightness": "bright:up",
    "decrease brightness": "bright:down",
    "switch to hand mode": "mode:hand",
    "switch to eye mode": "mode:eye",
    "switch to hybrid mode": "mode:hybrid",
    "switch to adaptive mode": "mode:adaptive",
    "pause tracking": "ctrl:pause",
    "resume tracking": "ctrl:resume",
    "left click": "mouse:left",
    "right click": "mouse:right",
    "double click": "mouse:double",
    "scroll up": "mouse:scroll_up",
    "scroll down": "mouse:scroll_down",
    "next tab": "key:next_tab",
    "previous tab": "key:prev_tab",
    "switch window": "key:switch_window",
    "confirm": "key:enter",
    "cancel": "key:escape",
    "take screenshot": "key:screenshot",
}


class VoiceEngine:
    """
    Background voice recognition engine.
    Uses microphone input and matches to VOICE_COMMANDS.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._command_queue: queue.Queue = queue.Queue()
        self._available = False
        self._engine_type = "none"

        self.on_command: Optional[Callable[[str, str], None]] = None
        self.on_status: Optional[Callable[[str], None]] = None

    def check_availability(self) -> bool:
        """Check if voice recognition is available."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as _:
                pass
            self._available = True
            self._engine_type = "sphinx"
            return True
        except Exception:
            pass

        try:
            import vosk
            self._available = True
            self._engine_type = "vosk"
            return True
        except Exception:
            pass

        logger.info("Voice control not available (no speech recognition library found)")
        return False

    def start(self):
        if self._running:
            return
        if not self.check_availability():
            if self.on_status:
                self.on_status("Voice: Not available")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        if self.on_status:
            self.on_status(f"Voice: Active ({self._engine_type})")

    def stop(self):
        self._running = False

    def _listen_loop(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True

            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Voice engine listening...")

                while self._running:
                    try:
                        audio = r.listen(source, timeout=2, phrase_time_limit=4)
                        try:
                            text = r.recognize_sphinx(audio).lower().strip()
                            self._process_text(text)
                        except sr.UnknownValueError:
                            pass
                        except Exception as e:
                            logger.debug(f"Voice recognition error: {e}")
                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        logger.debug(f"Listen error: {e}")

        except Exception as e:
            logger.warning(f"Voice engine failed: {e}")
            if self.on_status:
                self.on_status("Voice: Error")

    def _process_text(self, text: str):
        logger.debug(f"Voice heard: '{text}'")
        for phrase, command in VOICE_COMMANDS.items():
            if phrase in text:
                logger.info(f"Voice command: {phrase} → {command}")
                if self.on_command:
                    self.on_command(phrase, command)
                self._execute_command(command)
                return

    def _execute_command(self, command: str):
        from utils.system_control import get_controller
        from utils.app_scanner import find_app_by_name
        import os

        ctrl = get_controller()
        parts = command.split(":")

        if len(parts) < 2:
            return

        category, action = parts[0], parts[1]

        if category == "vol":
            if action == "up":
                ctrl.increase_volume()
            elif action == "down":
                ctrl.decrease_volume()

        elif category == "bright":
            if action == "up":
                ctrl.increase_brightness()
            elif action == "down":
                ctrl.decrease_brightness()

        elif category == "mouse":
            if action == "left":
                ctrl.left_click()
            elif action == "right":
                ctrl.right_click()
            elif action == "double":
                ctrl.double_click()
            elif action == "scroll_up":
                ctrl.scroll(5)
            elif action == "scroll_down":
                ctrl.scroll(-5)

        elif category == "key":
            key_map = {
                "next_tab": lambda: ctrl.next_tab(),
                "prev_tab": lambda: ctrl.prev_tab(),
                "switch_window": lambda: ctrl.switch_window(),
                "enter": lambda: ctrl.press_key("enter"),
                "escape": lambda: ctrl.press_key("escape"),
                "screenshot": lambda: ctrl.hotkey("win", "shift", "s"),
            }
            if action in key_map:
                key_map[action]()

        elif category == "app":
            app_names = {
                "chrome": "Google Chrome",
                "vscode": "Visual Studio Code",
                "notepad": "Notepad",
                "spotify": "Spotify",
                "calculator": "Calculator",
            }
            app_name = app_names.get(action, action)
            app = find_app_by_name(app_name)
            if app and app.get("path"):
                try:
                    ctrl.open_application(app["path"])
                except Exception as e:
                    logger.warning(f"Could not open app {app_name}: {e}")

    @property
    def is_active(self) -> bool:
        return self._running and self._available
