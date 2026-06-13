"""
VisionOS AI - Profile Manager
"""

from database.db_manager import (
    get_all_profiles, create_profile, get_setting,
    set_setting, get_default_profile_id
)


class ProfileManager:
    def __init__(self):
        self._active_id = get_default_profile_id()

    @property
    def active_id(self):
        return self._active_id

    def set_active(self, profile_id):
        self._active_id = profile_id

    def get_all(self):
        return get_all_profiles()

    def create(self, name):
        return create_profile(name)

    def get_setting(self, key, default=None):
        return get_setting(self._active_id, key, default)

    def set_setting(self, key, value):
        set_setting(self._active_id, key, value)

    def get_all_settings(self):
        keys = ["cursor_speed","smoothing","camera_index","hand_conf","eye_conf","click_cooldown"]
        defaults = {"cursor_speed":1.0,"smoothing":0.6,"camera_index":0,
                    "hand_conf":0.7,"eye_conf":0.7,"click_cooldown":0.4}
        return {k: get_setting(self._active_id, k, defaults.get(k)) for k in keys}
