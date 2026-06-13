"""
VisionOS AI - Startup / Home Window
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import sys
import os
from typing import Callable, Optional

from .theme import *

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class StartupWindow(ctk.CTk):
    """Main startup window with mode selection."""

    def __init__(self):
        super().__init__()

        self.title("VisionOS AI")
        self.geometry("900x650")
        self.minsize(800, 580)
        self.configure(fg_color=BG_DARK)
        self.resizable(True, True)

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 900) // 2
        y = (self.winfo_screenheight() - 650) // 2
        self.geometry(f"900x650+{x}+{y}")

        self._on_mode_select: Optional[Callable[[str], None]] = None
        self._on_settings: Optional[Callable[[], None]] = None

        self._build_ui()

    def _build_ui(self):
        # Left panel - branding
        left = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, width=340)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._build_left_panel(left)

        # Right panel - mode selection
        right = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        self._build_right_panel(right)

    def _build_left_panel(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Animated eye icon
        eye_canvas = tk.Canvas(inner, width=90, height=90,
                                bg=BG_CARD, highlightthickness=0)
        eye_canvas.pack(pady=(0, 20))
        self._draw_eye_logo(eye_canvas)

        ctk.CTkLabel(inner, text="VisionOS", font=FONT_TITLE,
                     text_color=ACCENT_CYAN).pack()
        ctk.CTkLabel(inner, text="AI", font=("Segoe UI", 38, "bold"),
                     text_color=ACCENT_BLUE).pack(pady=(0, 8))

        ctk.CTkLabel(inner, text="Intelligent Multimodal\nHands-Free Computer Control",
                     font=FONT_TAGLINE, text_color=TEXT_SECONDARY,
                     justify="center").pack(pady=(0, 30))

        # Version badge
        version_frame = ctk.CTkFrame(inner, fg_color=BG_SURFACE, corner_radius=20)
        version_frame.pack()
        ctk.CTkLabel(version_frame, text="  v1.0.0  Production  ",
                     font=FONT_XS, text_color=ACCENT_GREEN).pack(pady=4, padx=8)

        # Status indicator
        self._cam_status_label = ctk.CTkLabel(
            parent, text="● Camera: Checking...",
            font=FONT_XS, text_color=TEXT_MUTED
        )
        self._cam_status_label.pack(side="bottom", pady=10)
        self._check_camera()

    def _draw_eye_logo(self, canvas):
        """Draw the VisionOS eye logo."""
        cx, cy = 45, 45
        # Outer glow
        canvas.create_oval(5, 20, 85, 70, outline=ACCENT_CYAN, width=2, fill=BG_CARD)
        # Pupil
        canvas.create_oval(30, 30, 60, 60, outline=ACCENT_BLUE, width=2,
                           fill=BG_SURFACE)
        canvas.create_oval(38, 38, 52, 52, fill=ACCENT_CYAN, outline="")
        # Highlight
        canvas.create_oval(42, 40, 47, 45, fill="white", outline="")

    def _check_camera(self):
        def check():
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.release()
                self.after(0, lambda: self._cam_status_label.configure(
                    text="● Camera: Ready", text_color=ACCENT_GREEN))
            else:
                self.after(0, lambda: self._cam_status_label.configure(
                    text="● Camera: Not Found", text_color=ACCENT_RED))
        threading.Thread(target=check, daemon=True).start()

    def _build_right_panel(self, parent):
        # Header
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(30, 10))

        ctk.CTkLabel(header, text="Select Control Mode",
                     font=FONT_LG, text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(header, text="Choose how you want to control your computer",
                     font=FONT_XS, text_color=TEXT_SECONDARY).pack(side="left", padx=(15, 0))

        # Scrollable mode cards
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        modes = [
            {
                "id": "hand",
                "title": "Hand Gesture Mode",
                "icon": "🖐",
                "color": ACCENT_CYAN,
                "desc": "Control your PC using hand gestures via webcam.\nSupports click, drag, scroll, swipe and more.",
                "badges": ["MediaPipe", "OpenCV", "30-60 FPS"]
            },
            {
                "id": "eye",
                "title": "Eye Tracking Mode",
                "icon": "👁",
                "color": ACCENT_PURPLE,
                "desc": "Move cursor with your gaze. Blink to click.\nIncludes calibration wizard for accuracy.",
                "badges": ["Face Mesh", "Iris Tracking", "Blink Detection"]
            },
            {
                "id": "hybrid",
                "title": "Hybrid Mode",
                "icon": "🤝",
                "color": ACCENT_GREEN,
                "desc": "Eyes select target, hand confirms action.\nThe most precise and natural control method.",
                "badges": ["Eye + Hand", "High Accuracy", "Recommended"]
            },
            {
                "id": "adaptive",
                "title": "Adaptive AI Mode",
                "icon": "🧠",
                "color": ACCENT_ORANGE,
                "desc": "AI automatically picks the best mode.\nSwitches seamlessly between hand and eye.",
                "badges": ["Auto Switch", "AI Powered", "Smart"]
            },
        ]

        for mode in modes:
            self._build_mode_card(scroll, mode)

        # Bottom bar
        bottom = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0, height=60)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        ctk.CTkButton(bottom, text="⚙ Settings", width=120, height=36,
                      fg_color=BG_SURFACE, hover_color=BG_HOVER,
                      text_color=TEXT_SECONDARY, font=FONT_SM,
                      command=self._open_settings).pack(side="right", padx=15, pady=12)

        ctk.CTkButton(bottom, text="✕ Exit", width=100, height=36,
                      fg_color="#1A0A0A", hover_color="#2D1010",
                      text_color=ACCENT_RED, font=FONT_SM,
                      command=self._exit).pack(side="right", padx=5, pady=12)

        # Mode count label
        ctk.CTkLabel(bottom, text=f"4 modes available  •  MediaPipe powered  •  100% offline",
                     font=FONT_XS, text_color=TEXT_MUTED).pack(side="left", padx=15)

    def _build_mode_card(self, parent, mode: dict):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12,
                             border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", padx=5, pady=6)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=14)

        # Left: icon + info
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        icon_frame = ctk.CTkFrame(left, fg_color=BG_SURFACE, corner_radius=10,
                                   width=52, height=52)
        icon_frame.pack(side="left", padx=(0, 14))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text=mode["icon"], font=("Segoe UI", 22)).pack(
            expand=True)

        text_frame = ctk.CTkFrame(left, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(text_frame, text=mode["title"],
                     font=("Segoe UI", 14, "bold"),
                     text_color=mode["color"]).pack(anchor="w")

        ctk.CTkLabel(text_frame, text=mode["desc"],
                     font=FONT_XS, text_color=TEXT_SECONDARY,
                     justify="left").pack(anchor="w", pady=(3, 6))

        badges_frame = ctk.CTkFrame(text_frame, fg_color="transparent")
        badges_frame.pack(anchor="w")
        for badge in mode["badges"]:
            b = ctk.CTkFrame(badges_frame, fg_color=BG_SURFACE, corner_radius=10)
            b.pack(side="left", padx=(0, 5))
            ctk.CTkLabel(b, text=badge, font=FONT_XS,
                         text_color=TEXT_MUTED).pack(padx=7, pady=2)

        # Right: launch button
        btn = ctk.CTkButton(
            inner,
            text="Launch →",
            width=110,
            height=40,
            fg_color=mode["color"],
            hover_color=_darken(mode["color"]),
            text_color="#000000" if mode["color"] in (ACCENT_CYAN, ACCENT_GREEN, ACCENT_ORANGE) else TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            corner_radius=8,
            command=lambda m=mode["id"]: self._launch_mode(m)
        )
        btn.pack(side="right")

        # Hover effect
        def on_enter(e):
            card.configure(border_color=mode["color"])
        def on_leave(e):
            card.configure(border_color=BORDER_COLOR)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def _launch_mode(self, mode_id: str):
        if self._on_mode_select:
            self._on_mode_select(mode_id)

    def _open_settings(self):
        if self._on_settings:
            self._on_settings()
        else:
            SettingsDialog(self)

    def _exit(self):
        if messagebox.askyesno("Exit", "Exit VisionOS AI?"):
            self.destroy()
            sys.exit(0)

    def set_mode_callback(self, cb: Callable[[str], None]):
        self._on_mode_select = cb

    def set_settings_callback(self, cb: Callable[[], None]):
        self._on_settings = cb


def _darken(hex_color: str, factor: float = 0.75) -> str:
    """Darken a hex color by factor."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color
