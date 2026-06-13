"""
VisionOS AI - Application Scanner
Discovers installed apps and desktop shortcuts on Windows
"""

import os
import sys
import glob
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def get_desktop_icons() -> List[Dict]:
    """Return list of desktop shortcuts/icons."""
    icons = []

    desktop_paths = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
    ]

    for dp in desktop_paths:
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            full = os.path.join(dp, f)
            if f.endswith(('.lnk', '.exe', '.url')):
                name = os.path.splitext(f)[0]
                icons.append({"name": name, "path": full, "type": "desktop"})

    return icons


def get_common_apps() -> List[Dict]:
    """Return list of well-known Windows applications."""
    apps = []

    common = [
        ("Google Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ("Microsoft Edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ("Firefox", r"C:\Program Files\Mozilla Firefox\firefox.exe"),
        ("Visual Studio Code", os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Microsoft VS Code\Code.exe")),
        ("Notepad", r"C:\Windows\System32\notepad.exe"),
        ("Calculator", r"C:\Windows\System32\calc.exe"),
        ("Paint", r"C:\Windows\System32\mspaint.exe"),
        ("File Explorer", r"C:\Windows\explorer.exe"),
        ("Task Manager", r"C:\Windows\System32\taskmgr.exe"),
        ("Command Prompt", r"C:\Windows\System32\cmd.exe"),
        ("PowerShell", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"),
        ("Spotify", os.path.join(os.environ.get("APPDATA", ""), r"Spotify\Spotify.exe")),
        ("Discord", os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Discord\Update.exe")),
        ("VLC", r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
        ("Word", r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"),
        ("Excel", r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"),
        ("PowerPoint", r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"),
    ]

    for name, path in common:
        if os.path.exists(path):
            apps.append({"name": name, "path": path, "type": "installed"})

    return apps


def get_all_launchable_apps() -> List[Dict]:
    """Combine desktop icons and known apps."""
    seen = set()
    results = []

    for item in get_desktop_icons() + get_common_apps():
        key = item["path"].lower()
        if key not in seen:
            seen.add(key)
            results.append(item)

    results.sort(key=lambda x: x["name"].lower())
    return results


def find_app_by_name(name: str) -> Dict:
    """Fuzzy match app by name."""
    name_lower = name.lower()
    apps = get_all_launchable_apps()
    for app in apps:
        if name_lower in app["name"].lower():
            return app
    return {}
