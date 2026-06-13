"""
VisionOS AI - Main Application
Entry point that bootstraps the UI and wires all components
"""

import sys
import os
import logging
import threading
import tkinter as tk
from tkinter import messagebox

# ── Setup path ─────────────────────────────────────────────────────────────────
# Ensure the project root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── Logging ────────────────────────────────────────────────────────────────────
log_dir = os.path.join(os.path.expanduser("~"), ".visionos_ai")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "visionos.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("VisionOS")


def check_dependencies():
    """Check that required packages are installed."""
    missing = []
    required = {
        "cv2": "opencv-python",
        "mediapipe": "mediapipe",
        "customtkinter": "customtkinter",
        "PIL": "Pillow",
        "numpy": "numpy",
        "pyautogui": "pyautogui",
    }
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("\n" + "="*60)
        print("MISSING DEPENDENCIES")
        print("="*60)
        print("Please install the following packages:\n")
        print(f"  pip install {' '.join(missing)}\n")
        print("Or run:  pip install -r requirements.txt")
        print("="*60 + "\n")
        return False
    return True


class VisionOSApp:
    """Main application controller."""

    def __init__(self):
        self._startup_window = None
        self._dashboard_window = None
        self._engine = None
        self._profile_id = 1
        self._settings = {}

    def run(self):
        """Start the application."""
        # Check dependencies
        if not check_dependencies():
            input("Press Enter to exit...")
            sys.exit(1)

        # Initialize database
        try:
            from database.db_manager import init_database, get_default_profile_id, get_setting
            init_database()
            self._profile_id = get_default_profile_id()
            self._load_settings()
        except Exception as e:
            logger.error(f"Database init failed: {e}")

        # Launch startup UI
        self._show_startup()

    def _load_settings(self):
        try:
            from database.db_manager import get_setting
            pid = self._profile_id
            self._settings = {
                "cursor_speed":     get_setting(pid, "cursor_speed", 1.0),
                "smoothing":        get_setting(pid, "smoothing", 0.6),
                "camera_index":     get_setting(pid, "camera_index", 0),
                "hand_conf":        get_setting(pid, "hand_conf", 0.7),
                "eye_conf":         get_setting(pid, "eye_conf", 0.7),
                "click_cooldown":   get_setting(pid, "click_cooldown", 0.4),
            }
        except Exception:
            self._settings = {}

    def _show_startup(self):
        """Show the main startup window."""
        from ui.startup_window import StartupWindow
        from ui.settings_window import SettingsWindow

        self._startup_window = StartupWindow()
        self._startup_window.set_mode_callback(self._on_mode_selected)
        self._startup_window.set_settings_callback(
            lambda: SettingsWindow(self._startup_window, self._profile_id)
        )

        self._startup_window.mainloop()

    def _on_mode_selected(self, mode: str):
        """Called when user selects a mode."""
        logger.info(f"Mode selected: {mode}")

        # If eye mode, offer calibration first
        if mode in ("eye", "hybrid"):
            self._check_eye_calibration(mode)
        else:
            self._launch_mode(mode)

    def _check_eye_calibration(self, mode: str):
        """Check if calibration is needed for eye modes."""
        try:
            from database.db_manager import get_calibration
            calib = get_calibration(self._profile_id, "eye")
            if calib:
                self._launch_mode(mode)
                return
        except Exception:
            pass

        # Ask for calibration
        if self._startup_window:
            answer = messagebox.askyesno(
                "Eye Calibration Required",
                "Eye tracking works best with calibration.\n\n"
                "Run the calibration wizard now?\n\n"
                "(You can skip this and calibrate later in Settings)",
                parent=self._startup_window
            )
            if answer:
                self._run_calibration(mode)
            else:
                self._launch_mode(mode)
        else:
            self._launch_mode(mode)

    def _run_calibration(self, mode: str):
        """Launch calibration wizard."""
        try:
            from ui.calibration_wizard import CalibrationWizard
            from eye_tracking.eye_detector import EyeDetector

            # Create a temporary eye detector for calibration
            eye_det = EyeDetector()
            eye_det.initialize()

            wizard = CalibrationWizard(
                self._startup_window, eye_det,
                on_complete=lambda _: (eye_det.release(), self._launch_mode(mode))
            )
            wizard.focus_force()
        except Exception as e:
            logger.error(f"Calibration error: {e}")
            self._launch_mode(mode)

    def _launch_mode(self, mode: str):
        """Create VisionEngine and show dashboard."""
        try:
            import pyautogui
            sw, sh = pyautogui.size()

            from computer_vision.vision_engine import VisionEngine
            from ui.dashboard_window import DashboardWindow

            self._load_settings()

            # Create engine
            self._engine = VisionEngine(
                mode=mode,
                screen_w=sw,
                screen_h=sh,
                profile_id=self._profile_id,
                settings=self._settings
            )

            # Show startup window in background
            if self._startup_window:
                self._startup_window.withdraw()

            # Create dashboard
            self._dashboard_window = DashboardWindow(
                parent=self._startup_window,
                mode=mode,
                on_stop=self._on_mode_stopped
            )
            self._dashboard_window.set_engine(self._engine)

            # Start voice control (optional)
            self._start_voice_control(mode)

        except Exception as e:
            logger.error(f"Failed to launch mode '{mode}': {e}", exc_info=True)
            messagebox.showerror("Launch Error",
                f"Failed to start '{mode}' mode:\n\n{e}\n\n"
                "Please check that your webcam is connected and try again.")
            if self._startup_window:
                self._startup_window.deiconify()

    def _start_voice_control(self, mode: str):
        """Start voice control in background."""
        def _start():
            try:
                from voice_control.voice_engine import VoiceEngine
                self._voice = VoiceEngine()
                self._voice.on_status = lambda s: logger.info(s)
                self._voice.on_command = lambda phrase, cmd: logger.info(
                    f"Voice command: {phrase} → {cmd}")
                self._voice.start()
            except Exception as e:
                logger.debug(f"Voice control not started: {e}")
        threading.Thread(target=_start, daemon=True).start()

    def _on_mode_stopped(self):
        """Called when user stops the active mode."""
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None

        if self._startup_window and self._startup_window.winfo_exists():
            self._startup_window.deiconify()
            self._startup_window.lift()


def main():
    """Application entry point."""
    logger.info("="*50)
    logger.info("VisionOS AI Starting...")
    logger.info("="*50)

    try:
        app = VisionOSApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("VisionOS AI stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        try:
            messagebox.showerror("Fatal Error",
                f"VisionOS AI encountered a fatal error:\n\n{e}\n\n"
                "Check the log file at:\n"
                f"  {os.path.join(os.path.expanduser('~'), '.visionos_ai', 'visionos.log')}")
        except Exception:
            print(f"FATAL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
