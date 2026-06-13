"""
VisionOS AI - Basic Tests
Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_database_init():
    """Test database initializes without error."""
    from database.db_manager import init_database, get_default_profile_id
    init_database()
    pid = get_default_profile_id()
    assert isinstance(pid, int)
    assert pid >= 1
    print("✓ Database init OK")


def test_database_settings():
    """Test settings read/write."""
    from database.db_manager import init_database, get_setting, set_setting, get_default_profile_id
    init_database()
    pid = get_default_profile_id()
    set_setting(pid, "test_key", 42)
    val = get_setting(pid, "test_key")
    assert val == 42
    print("✓ Settings read/write OK")


def test_smoothing():
    """Test cursor smoother."""
    from utils.smoothing import CursorSmoother, GestureBuffer, EyeSmoother
    s = CursorSmoother()
    x, y = s.smooth(100.0, 200.0)
    assert isinstance(x, float)
    assert isinstance(y, float)

    g = GestureBuffer(window=5)
    for _ in range(4):
        g.add("pinch")
    assert g.dominant() == "pinch"

    e = EyeSmoother()
    ex, ey = e.smooth(0.5, 0.5)
    assert 0 <= ex <= 1
    print("✓ Smoothing OK")


def test_system_controller():
    """Test system controller instantiates."""
    from utils.system_control import SystemController
    sc = SystemController()
    w, h = sc.get_screen_size()
    assert w > 0 and h > 0
    print(f"✓ System controller OK — screen: {w}x{h}")


def test_app_scanner():
    """Test app scanner runs without crash."""
    from utils.app_scanner import get_all_launchable_apps
    apps = get_all_launchable_apps()
    assert isinstance(apps, list)
    print(f"✓ App scanner OK — found {len(apps)} apps")


def test_hand_detector_import():
    """Test hand detector can be imported."""
    from gesture_engine.hand_detector import HandDetector, GESTURE_POINT, GESTURE_PINCH
    d = HandDetector()
    assert d is not None
    print("✓ HandDetector import OK")


def test_eye_detector_import():
    """Test eye detector can be imported."""
    from eye_tracking.eye_detector import EyeDetector, BLINK_SINGLE, BLINK_DOUBLE
    d = EyeDetector()
    assert d is not None
    print("✓ EyeDetector import OK")


def test_adaptive_controller():
    """Test adaptive controller logic."""
    from adaptive_ai.adaptive_controller import AdaptiveController, MODE_HAND, MODE_EYE, MODE_HYBRID

    ac = AdaptiveController()
    # Simulate fast mode switching (bypass stability timer)
    ac._mode_stable_duration = 0.0

    ac.update(hand_detected=True, eye_detected=False)
    ac.update(hand_detected=True, eye_detected=False)
    assert ac.active_mode == MODE_HAND

    ac.update(hand_detected=False, eye_detected=True)
    ac.update(hand_detected=False, eye_detected=True)
    assert ac.active_mode == MODE_EYE

    ac.update(hand_detected=True, eye_detected=True)
    ac.update(hand_detected=True, eye_detected=True)
    assert ac.active_mode == MODE_HYBRID

    print("✓ AdaptiveController logic OK")


def test_camera_thread_import():
    """Test camera thread can be imported."""
    from computer_vision.camera_thread import CameraThread
    ct = CameraThread(camera_index=0)
    assert ct is not None
    print("✓ CameraThread import OK")


def run_all():
    tests = [
        test_database_init,
        test_database_settings,
        test_smoothing,
        test_system_controller,
        test_app_scanner,
        test_hand_detector_import,
        test_eye_detector_import,
        test_adaptive_controller,
        test_camera_thread_import,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__} FAILED: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
