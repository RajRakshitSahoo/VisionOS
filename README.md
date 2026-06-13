# VisionOS AI 🖐👁🧠

**Intelligent Multimodal Hands-Free Computer Control System**

Control your entire computer without touching a mouse or keyboard — using hand gestures, eye tracking, or both.

---

## Features

- **4 Control Modes**: Hand Gesture, Eye Tracking, Hybrid, Adaptive AI
- **Full Mouse Control**: Move, click, right-click, double-click, drag & drop, scroll
- **Keyboard Shortcuts**: Tab switching, window switching, volume, brightness
- **AI Intent Prediction**: Suggests apps based on your usage patterns
- **Voice Commands**: Optional offline voice control
- **User Profiles**: Saves calibration, preferences, and gesture history
- **100% Offline**: No cloud, no internet required

---

## Requirements

- Windows 10/11
- Python 3.9 – 3.11 (recommended: 3.10)
- Webcam (built-in or USB)
- 4GB RAM minimum

---

## Installation

### Step 1: Install Python

Download Python 3.10 from https://www.python.org/downloads/
During install, check ✅ "Add Python to PATH"

### Step 2: Clone or extract the project

```
cd C:\Users\YourName\Desktop
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

If you have issues with mediapipe on Python 3.12+, use Python 3.10:
```bash
py -3.10 -m pip install -r requirements.txt
```

### Step 4: Run

```bash
python app.py
```

Or double-click `run.bat`

---

## Gesture Reference

| Gesture | Action |
|---------|--------|
| ☝ Index Finger | Move Cursor |
| 🤏 Thumb+Index Pinch | Left Click |
| ✌ Index+Middle Pinch | Right Click |
| 🤏🤏 Double Pinch | Double Click |
| ✊ Closed Fist | Drag & Drop |
| 🖐 Open Palm | Pause/Resume |
| → Swipe Right | Next Tab |
| ← Swipe Left | Previous Tab |
| 👍 Thumbs Up | Confirm (Enter) |
| 👎 Thumbs Down | Cancel (Escape) |

## Eye Tracking

| Action | Result |
|--------|--------|
| Gaze | Move Cursor |
| Single Blink | Left Click |
| Double Blink | Open / Double Click |
| Long Blink (>0.4s) | Right Click |

---

## Voice Commands (Optional)

Requires: `pip install SpeechRecognition pyaudio`

| Say | Action |
|-----|--------|
| "Open Chrome" | Opens Chrome |
| "Increase Volume" | Volume Up |
| "Switch to Eye Mode" | Changes mode |
| "Pause Tracking" | Pauses input |
| "Left Click" | Clicks mouse |

---

## Project Structure

```
visionos_ai/
├── app.py                    # Entry point
├── requirements.txt
├── run.bat                   # Windows launcher
├── ui/                       # CustomTkinter UI
│   ├── startup_window.py
│   ├── dashboard_window.py
│   ├── settings_window.py
│   └── calibration_wizard.py
├── computer_vision/          # Camera + engine
│   ├── camera_thread.py
│   └── vision_engine.py
├── gesture_engine/           # Hand detection
│   ├── hand_detector.py
│   └── gesture_controller.py
├── eye_tracking/             # Eye/gaze detection
│   ├── eye_detector.py
│   └── eye_controller.py
├── adaptive_ai/              # Auto mode switching
│   └── adaptive_controller.py
├── voice_control/            # Offline voice
│   └── voice_engine.py
├── database/                 # SQLite
│   └── db_manager.py
└── utils/                    # Shared utilities
    ├── system_control.py
    ├── smoothing.py
    └── app_scanner.py
```

---

## Troubleshooting

**Camera not found**
- Check camera is connected and not used by another app
- Try changing Camera Index in Settings (0, 1, 2...)

**Hand not detected**
- Ensure good lighting
- Keep hand 30–60 cm from camera
- Lower detection confidence in Settings

**Eye tracking inaccurate**
- Run calibration (Settings → Eye Track → Run Calibration)
- Ensure face is well lit and camera is at eye level

**mediapipe install fails**
- Use Python 3.10: `py -3.10 -m pip install mediapipe`
- Or: `pip install mediapipe==0.10.9`

**pyautogui permission error**
- Run VS Code / terminal as Administrator

---

## Log File

Logs are saved to: `C:\Users\<YourName>\.visionos_ai\visionos.log`

---

## License

MIT License — Free to use and modify.
