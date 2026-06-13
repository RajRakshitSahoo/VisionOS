"""
VisionOS AI - Database Manager
Handles all SQLite operations via SQLAlchemy
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path


DB_PATH = Path(os.path.expanduser("~")) / ".visionos_ai" / "visionos.db"


def get_db_path():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return str(DB_PATH)


def init_database():
    """Initialize all database tables."""
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()

    # User profiles
    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            settings TEXT DEFAULT '{}'
        )
    """)

    # Calibration data
    c.execute("""
        CREATE TABLE IF NOT EXISTS calibration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    """)

    # Custom gestures
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_gestures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            gesture_data TEXT NOT NULL,
            action TEXT NOT NULL,
            action_params TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    """)

    # App usage history
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            app_name TEXT NOT NULL,
            app_path TEXT,
            open_count INTEGER DEFAULT 1,
            last_opened TEXT NOT NULL,
            hour_of_day INTEGER,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    """)

    # Gesture usage history
    c.execute("""
        CREATE TABLE IF NOT EXISTS gesture_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            gesture_name TEXT NOT NULL,
            use_count INTEGER DEFAULT 1,
            last_used TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    """)

    # Settings
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(profile_id, key),
            FOREIGN KEY (profile_id) REFERENCES profiles(id)
        )
    """)

    conn.commit()
    conn.close()

    # Create default profile if none exists
    _ensure_default_profile()


def _ensure_default_profile():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id FROM profiles WHERE name='Default'")
    if not c.fetchone():
        now = datetime.now().isoformat()
        c.execute("INSERT INTO profiles (name, created_at, updated_at, settings) VALUES (?,?,?,?)",
                  ("Default", now, now, "{}"))
        conn.commit()
    conn.close()


def get_default_profile_id():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id FROM profiles WHERE name='Default'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 1


def get_all_profiles():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, name, created_at FROM profiles ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return rows


def create_profile(name: str) -> int:
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT OR IGNORE INTO profiles (name, created_at, updated_at, settings) VALUES (?,?,?,?)",
              (name, now, now, "{}"))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return pid


def get_setting(profile_id: int, key: str, default=None):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE profile_id=? AND key=?", (profile_id, key))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]
    return default


def set_setting(profile_id: int, key: str, value):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    c.execute("INSERT OR REPLACE INTO settings (profile_id, key, value) VALUES (?,?,?)",
              (profile_id, key, val_str))
    conn.commit()
    conn.close()


def save_calibration(profile_id: int, mode: str, data: dict):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    # Remove old calibration for this mode
    c.execute("DELETE FROM calibration WHERE profile_id=? AND mode=?", (profile_id, mode))
    now = datetime.now().isoformat()
    c.execute("INSERT INTO calibration (profile_id, mode, data, created_at) VALUES (?,?,?,?)",
              (profile_id, mode, json.dumps(data), now))
    conn.commit()
    conn.close()


def get_calibration(profile_id: int, mode: str) -> dict:
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT data FROM calibration WHERE profile_id=? AND mode=?", (profile_id, mode))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else {}


def record_app_usage(profile_id: int, app_name: str, app_path: str = ""):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    now = datetime.now().isoformat()
    hour = datetime.now().hour
    c.execute("SELECT id, open_count FROM app_history WHERE profile_id=? AND app_name=?",
              (profile_id, app_name))
    row = c.fetchone()
    if row:
        c.execute("UPDATE app_history SET open_count=?, last_opened=?, hour_of_day=? WHERE id=?",
                  (row[1] + 1, now, hour, row[0]))
    else:
        c.execute("INSERT INTO app_history (profile_id, app_name, app_path, open_count, last_opened, hour_of_day) VALUES (?,?,?,1,?,?)",
                  (profile_id, app_name, app_path, now, hour))
    conn.commit()
    conn.close()


def get_frequent_apps(profile_id: int, limit: int = 5):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    hour = datetime.now().hour
    # Weight by both frequency and time-of-day match
    c.execute("""
        SELECT app_name, app_path, open_count,
               CASE WHEN ABS(hour_of_day - ?) <= 2 THEN open_count * 2 ELSE open_count END as score
        FROM app_history WHERE profile_id=?
        ORDER BY score DESC LIMIT ?
    """, (hour, profile_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def save_custom_gesture(profile_id: int, name: str, gesture_data: dict, action: str, action_params: dict = {}):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT OR REPLACE INTO custom_gestures (profile_id, name, gesture_data, action, action_params, created_at) VALUES (?,?,?,?,?,?)",
              (profile_id, name, json.dumps(gesture_data), action, json.dumps(action_params), now))
    conn.commit()
    conn.close()


def get_custom_gestures(profile_id: int):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, name, gesture_data, action, action_params FROM custom_gestures WHERE profile_id=?",
              (profile_id,))
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "gesture_data": json.loads(row[2]),
            "action": row[3],
            "action_params": json.loads(row[4])
        })
    return result
