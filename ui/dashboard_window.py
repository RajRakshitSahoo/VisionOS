"""
VisionOS AI - Dashboard Window
Live control dashboard with webcam feed, status panels, and controls
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import cv2
from PIL import Image, ImageTk
import numpy as np
from typing import Optional, Dict, Callable
import queue

from .theme import *

MODE_LABELS = {
    "hand": "🖐 Hand Gesture",
    "eye": "👁 Eye Tracking",
    "hybrid": "🤝 Hybrid",
    "adaptive": "🧠 Adaptive AI",
    "none": "⚠ No Input",
}

MODE_COLORS = {
    "hand": ACCENT_CYAN,
    "eye": ACCENT_PURPLE,
    "hybrid": ACCENT_GREEN,
    "adaptive": ACCENT_ORANGE,
    "none": TEXT_MUTED,
}


class DashboardWindow(ctk.CTkToplevel):
    """Live dashboard shown while VisionOS is active."""

    def __init__(self, parent, mode: str, on_stop: Callable = None):
        super().__init__(parent)

        self._mode = mode
        self._on_stop = on_stop
        self._engine = None
        self._running = False

        # Notification queue
        self._notif_queue: queue.Queue = queue.Queue(maxsize=10)
        self._notifications = []

        self.title(f"VisionOS AI — {MODE_LABELS.get(mode, mode)}")
        self.geometry("1200x720")
        self.minsize(1000, 620)
        self.configure(fg_color=BG_DARK)
        self.protocol("WM_DELETE_WINDOW", self._stop_and_close)

        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1200) // 2
        y = (self.winfo_screenheight() - 720) // 2
        self.geometry(f"1200x720+{x}+{y}")

        self._build_ui()
        self._start_ui_loop()

    def _build_ui(self):
        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=56)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self._build_topbar(topbar)

        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)

        # Left: camera feed
        left = ctk.CTkFrame(content, fg_color=BG_CARD, corner_radius=12)
        left.pack(side="left", fill="both", expand=True)
        self._build_camera_panel(left)

        # Right: status panel
        right = ctk.CTkFrame(content, fg_color="transparent", width=300)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)
        self._build_status_panel(right)

    def _build_topbar(self, parent):
        # Logo
        ctk.CTkLabel(parent, text="⬡ VisionOS AI",
                     font=("Segoe UI", 16, "bold"),
                     text_color=ACCENT_CYAN).pack(side="left", padx=18)

        # Mode badge
        mode_color = MODE_COLORS.get(self._mode, TEXT_MUTED)
        self._mode_badge = ctk.CTkLabel(
            parent,
            text=f"  {MODE_LABELS.get(self._mode, self._mode)}  ",
            font=FONT_SM,
            fg_color=mode_color,
            text_color="#000000" if mode_color in (ACCENT_CYAN, ACCENT_GREEN, ACCENT_ORANGE) else TEXT_PRIMARY,
            corner_radius=12
        )
        self._mode_badge.pack(side="left", padx=8, pady=12)

        # Right side controls
        ctk.CTkButton(parent, text="⏹ Stop & Return", width=130, height=34,
                      fg_color=ACCENT_RED, hover_color="#B91C1C",
                      text_color="white", font=FONT_SM,
                      command=self._stop_and_close).pack(side="right", padx=18, pady=11)

        ctk.CTkButton(parent, text="⏸ Pause", width=90, height=34,
                      fg_color=BG_SURFACE, hover_color=BG_HOVER,
                      text_color=TEXT_SECONDARY, font=FONT_SM,
                      command=self._toggle_pause).pack(side="right", padx=4, pady=11)

        # FPS
        self._fps_label = ctk.CTkLabel(parent, text="FPS: --",
                                        font=FONT_MONO, text_color=ACCENT_GREEN)
        self._fps_label.pack(side="right", padx=18)

    def _build_camera_panel(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(header, text="📷 Live Camera Feed",
                     font=("Segoe UI", 13, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")
        self._cam_status = ctk.CTkLabel(header, text="● Starting...",
                                         font=FONT_XS, text_color=TEXT_MUTED)
        self._cam_status.pack(side="right")

        # Camera canvas
        self._cam_canvas = tk.Canvas(parent, bg="#050810",
                                      highlightthickness=1,
                                      highlightbackground=BORDER_COLOR)
        self._cam_canvas.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self._cam_image_id = None

        # Notification overlay at bottom
        self._notif_label = ctk.CTkLabel(
            parent, text="", font=("Segoe UI", 13, "bold"),
            text_color=ACCENT_CYAN, fg_color="transparent"
        )
        self._notif_label.pack(pady=(0, 8))

    def _build_status_panel(self, parent):
        # Store status label refs — must be initialised before _build_card is called
        self._status_labels: Dict[str, ctk.CTkLabel] = {}

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color=BG_SURFACE)
        scroll.pack(fill="both", expand=True)

        # Detection status card
        self._build_card(scroll, "🔍 Detection Status", [
            ("Hand", "hand_status", "○ Not detected", TEXT_MUTED),
            ("Eyes", "eye_status", "○ Not detected", TEXT_MUTED),
            ("Face", "face_status", "○ Not detected", TEXT_MUTED),
        ])

        # Gesture status card
        self._build_card(scroll, "🤌 Active Gesture", [
            ("Gesture", "gesture_status", "—", TEXT_SECONDARY),
            ("Confidence", "conf_status", "—", TEXT_SECONDARY),
        ])

        # Eye tracking card
        self._build_card(scroll, "👁 Eye Tracking", [
            ("Status", "eye_track_status", "—", TEXT_SECONDARY),
            ("EAR", "ear_status", "—", TEXT_SECONDARY),
            ("Blink", "blink_status", "—", TEXT_SECONDARY),
        ])

        # Performance card
        self._build_card(scroll, "⚡ Performance", [
            ("FPS", "fps_status", "—", TEXT_SECONDARY),
            ("Latency", "latency_status", "—", TEXT_SECONDARY),
            ("Mode", "mode_status", MODE_LABELS.get(self._mode, "—"), TEXT_SECONDARY),
        ])

        # Notifications card
        notif_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10)
        notif_card.pack(fill="x", pady=5)
        ctk.CTkLabel(notif_card, text="🔔 Recent Actions",
                     font=("Segoe UI", 12, "bold"),
                     text_color=TEXT_SECONDARY).pack(anchor="w", padx=12, pady=(10, 4))
        self._notif_list_frame = ctk.CTkFrame(notif_card, fg_color="transparent")
        self._notif_list_frame.pack(fill="x", padx=12, pady=(0, 8))

        # Quick controls
        ctrl_card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=10)
        ctrl_card.pack(fill="x", pady=5)
        ctk.CTkLabel(ctrl_card, text="🎛 Quick Controls",
                     font=("Segoe UI", 12, "bold"),
                     text_color=TEXT_SECONDARY).pack(anchor="w", padx=12, pady=(10, 4))

        for label, cmd in [
            ("Vol +", lambda: self._sys_action("vol_up")),
            ("Vol -", lambda: self._sys_action("vol_dn")),
            ("Bright +", lambda: self._sys_action("bright_up")),
            ("Bright -", lambda: self._sys_action("bright_dn")),
        ]:
            ctk.CTkButton(ctrl_card, text=label, height=30, width=200,
                          fg_color=BG_SURFACE, hover_color=BG_HOVER,
                          text_color=TEXT_SECONDARY, font=FONT_XS,
                          corner_radius=6,
                          command=cmd).pack(padx=12, pady=3)
        ctk.CTkFrame(ctrl_card, fg_color="transparent", height=6).pack()

    def _build_card(self, parent, title: str, rows: list):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.pack(fill="x", pady=5)

        ctk.CTkLabel(card, text=title, font=("Segoe UI", 12, "bold"),
                     text_color=TEXT_SECONDARY).pack(anchor="w", padx=12, pady=(10, 4))

        sep = ctk.CTkFrame(card, fg_color=BORDER_COLOR, height=1)
        sep.pack(fill="x", padx=12)

        for label, key, default, color in rows:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)
            ctk.CTkLabel(row, text=label + ":", font=FONT_XS,
                         text_color=TEXT_MUTED, width=80, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text=default, font=FONT_XS,
                               text_color=color, anchor="e")
            lbl.pack(side="right")
            self._status_labels[key] = lbl

        ctk.CTkFrame(card, fg_color="transparent", height=4).pack()

    def _start_ui_loop(self):
        """Start the UI update loop."""
        self._paused = False
        self._last_frame_time = time.time()
        self._update_ui()

    def _update_ui(self):
        if not self.winfo_exists():
            return

        # Update camera frame
        if self._engine:
            frame = self._engine.get_frame()
            if frame is not None:
                self._show_frame(frame)
                self._cam_status.configure(text="● Live", text_color=ACCENT_GREEN)

        # Process notifications
        while not self._notif_queue.empty():
            try:
                msg = self._notif_queue.get_nowait()
                self._add_notification(msg)
            except Exception:
                pass

        self.after(33, self._update_ui)  # ~30fps UI update

    def _show_frame(self, frame: np.ndarray):
        try:
            canvas_w = self._cam_canvas.winfo_width()
            canvas_h = self._cam_canvas.winfo_height()
            if canvas_w < 10 or canvas_h < 10:
                return

            h, w = frame.shape[:2]
            scale = min(canvas_w / w, canvas_h / h)
            new_w, new_h = int(w * scale), int(h * scale)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb).resize((new_w, new_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)

            self._cam_canvas.delete("all")
            ox = (canvas_w - new_w) // 2
            oy = (canvas_h - new_h) // 2
            self._cam_canvas.create_image(ox, oy, anchor="nw", image=photo)
            self._cam_canvas._photo = photo  # prevent GC

        except Exception:
            pass

    def update_status(self, status: dict):
        """Called from vision engine with status updates."""
        if not self.winfo_exists():
            return

        def _update():
            fps = status.get("fps", 0)
            self._fps_label.configure(
                text=f"FPS: {fps:.0f}",
                text_color=ACCENT_GREEN if fps >= 20 else ACCENT_ORANGE
            )

            hand = status.get("hand_detected", False)
            eye = status.get("eye_detected", False)
            gesture = status.get("gesture", "none")
            ear = status.get("ear", 1.0)
            conf = status.get("confidence", 0.0)

            def _set(key, text, color=TEXT_SECONDARY):
                lbl = self._status_labels.get(key)
                if lbl:
                    lbl.configure(text=text, text_color=color)

            _set("hand_status",
                 "● Detected" if hand else "○ Not detected",
                 ACCENT_GREEN if hand else TEXT_MUTED)
            _set("eye_status",
                 "● Detected" if eye else "○ Not detected",
                 ACCENT_GREEN if eye else TEXT_MUTED)
            _set("gesture_status", gesture.replace("_", " ").title(),
                 ACCENT_CYAN if gesture != "none" else TEXT_MUTED)
            _set("conf_status", f"{conf * 100:.0f}%",
                 ACCENT_GREEN if conf > 0.7 else ACCENT_ORANGE)
            _set("ear_status", f"{ear:.3f}",
                 ACCENT_GREEN if ear > 0.25 else ACCENT_RED)
            _set("fps_status", f"{fps:.0f}",
                 ACCENT_GREEN if fps >= 20 else ACCENT_ORANGE)

            active_mode = status.get("mode", self._mode)
            mode_lbl = MODE_LABELS.get(active_mode, active_mode)
            mode_color = MODE_COLORS.get(active_mode, TEXT_MUTED)
            _set("mode_status", mode_lbl, mode_color)

            # Update adaptive mode badge
            if self._mode == "adaptive":
                self._mode_badge.configure(
                    text=f"  {mode_lbl}  ",
                    fg_color=mode_color,
                    text_color="#000" if mode_color in (ACCENT_CYAN, ACCENT_GREEN, ACCENT_ORANGE) else TEXT_PRIMARY
                )

        self.after(0, _update)

    def add_notification(self, msg: str):
        """Thread-safe notification add."""
        try:
            self._notif_queue.put_nowait(msg)
        except queue.Full:
            pass

    def _add_notification(self, msg: str):
        """Add to notifications list in UI."""
        # Update main overlay
        self._notif_label.configure(text=msg)
        self.after(2500, lambda: self._notif_label.configure(text="") 
                   if self.winfo_exists() else None)

        # Add to notification list
        self._notifications.insert(0, msg)
        self._notifications = self._notifications[:6]

        # Rebuild list
        for child in self._notif_list_frame.winfo_children():
            child.destroy()

        for n in self._notifications:
            ctk.CTkLabel(self._notif_list_frame, text=n,
                         font=FONT_XS, text_color=TEXT_SECONDARY,
                         anchor="w").pack(fill="x", pady=1)

    def set_engine(self, engine):
        """Attach VisionEngine and start it."""
        self._engine = engine
        engine.on_frame = None  # we pull frames in UI loop
        engine.on_status = self.update_status
        engine.on_notify = self.add_notification
        engine.on_suggestion = self._show_suggestion
        engine.start()
        self._running = True

    def _show_suggestion(self, suggestion: dict):
        """Show AI intent suggestion."""
        msg = suggestion.get("message", "")
        if msg:
            self.add_notification(f"💡 {msg}")

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self.add_notification("⏸ Tracking paused")
        else:
            self.add_notification("▶ Tracking resumed")

    def _sys_action(self, action: str):
        from utils.system_control import get_controller
        ctrl = get_controller()
        actions = {
            "vol_up": ctrl.increase_volume,
            "vol_dn": ctrl.decrease_volume,
            "bright_up": ctrl.increase_brightness,
            "bright_dn": ctrl.decrease_brightness,
        }
        if action in actions:
            threading.Thread(target=actions[action], daemon=True).start()

    def _stop_and_close(self):
        if self._engine:
            self._engine.stop()
        if self._on_stop:
            self._on_stop()
        self.destroy()
