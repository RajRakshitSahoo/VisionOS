# Lazy imports — don't import at module level to avoid display issues
def get_controller():
    from .system_control import get_controller as _gc
    return _gc()

from .smoothing import CursorSmoother, EyeSmoother, GestureBuffer
from .app_scanner import get_all_launchable_apps, find_app_by_name
