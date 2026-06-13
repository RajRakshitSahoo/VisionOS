"""
VisionOS AI - Settings Window
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional
import threading

from .theme import *


class SettingsWindow(ctk.CTkToplevel):
    """Settings dialog for VisionOS AI."""

    def __init__(self, parent, profile_id: int = 1):
        super().__init__(parent)

        self._profile_id = profile_id
        self.title("VisionOS AI — Settings")
        self.geometry("720x580")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.grab_set()  # modal

        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 720) // 2
        y = (self.winfo_screenheight() - 580) // 2
        self.geometry(f"720x580+{x}+{y}")

        self._load_settings()
        self._build_ui()

    def _load_settings(self):
        try:
            from database.db_manager import get_setting
            self._cursor_speed = get_setting(self._profile_id, "cursor_speed", 1.0)
            self._smoothing = get_setting(self._profile_id, "smoothing", 0.6)
            self._camera_index = get_setting(self._profile_id, "camera_index", 0)
            self._hand_conf = get_setting(self._profile_id, "hand_conf", 0.7)
            self._eye_conf = get_setting(self._profile_id, "eye_conf", 0.7)
            self._click_cooldown = get_setting(self._profile_id, "click_cooldown", 0.4)
        except Exception:
            self._cursor_speed = 1.0
            self._smoothing = 0.6
            self._camera_index = 0
            self._hand_conf = 0.7
            self._eye_conf = 0.7
            self._click_cooldown = 0.4

    def _build_ui(self):
        # Title
        title_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=52)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        ctk.CTkLabel(title_bar, text="⚙ Settings",
                     font=FONT_LG, text_color=ACCENT_CYAN).pack(side="left", padx=18, pady=14)

        # Tab view
        tabs = ctk.CTkTabview(self, fg_color=BG_CARD,
                               segmented_button_fg_color=BG_SURFACE,
                               segmented_button_selected_color=ACCENT_BLUE)
        tabs.pack(fill="both", expand=True, padx=15, pady=10)

        # Tabs
        tabs.add("🖱 Cursor")
        tabs.add("📷 Camera")
        tabs.add("✋ Gestures")
        tabs.add("👁 Eye Track")
        tabs.add("👤 Profile")

        self._build_cursor_tab(tabs.tab("🖱 Cursor"))
        self._build_camera_tab(tabs.tab("📷 Camera"))
        self._build_gesture_tab(tabs.tab("✋ Gestures"))
        self._build_eye_tab(tabs.tab("👁 Eye Track"))
        self._build_profile_tab(tabs.tab("👤 Profile"))

        # Save/Cancel
        btn_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=52)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        ctk.CTkButton(btn_frame, text="Save Settings", width=130, height=36,
                      fg_color=ACCENT_GREEN, hover_color="#059669",
                      text_color="#000", font=FONT_SM,
                      command=self._save).pack(side="right", padx=15, pady=8)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, height=36,
                      fg_color=BG_SURFACE, hover_color=BG_HOVER,
                      text_color=TEXT_SECONDARY, font=FONT_SM,
                      command=self.destroy).pack(side="right", padx=5, pady=8)

    def _build_cursor_tab(self, parent):
        self._cursor_speed_var = ctk.DoubleVar(value=self._cursor_speed)
        self._smoothing_var = ctk.DoubleVar(value=self._smoothing)
        self._cooldown_var = ctk.DoubleVar(value=self._click_cooldown)

        self._slider_section(parent, "Cursor Speed", self._cursor_speed_var,
                             0.3, 2.0, "Slow ◄──────────── Fast")
        self._slider_section(parent, "Cursor Smoothing", self._smoothing_var,
                             0.0, 0.95, "None ◄──────────── Max")
        self._slider_section(parent, "Click Cooldown (sec)", self._cooldown_var,
                             0.1, 1.0, "Fast ◄──────────── Slow")

    def _build_camera_tab(self, parent):
        self._cam_idx_var = ctk.IntVar(value=self._camera_index)

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(row, text="Camera Index:", font=FONT_SM,
                     text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkEntry(row, textvariable=self._cam_idx_var, width=60,
                     fg_color=BG_SURFACE).pack(side="left", padx=10)

        ctk.CTkButton(parent, text="🔍 Test Camera", width=150, height=34,
                      fg_color=ACCENT_BLUE, command=self._test_camera
                      ).pack(padx=20, pady=5)

        self._cam_test_label = ctk.CTkLabel(parent, text="",
                                             font=FONT_XS, text_color=TEXT_SECONDARY)
        self._cam_test_label.pack(padx=20, pady=5)

    def _build_gesture_tab(self, parent):
        self._hand_conf_var = ctk.DoubleVar(value=self._hand_conf)

        self._slider_section(parent, "Hand Detection Confidence",
                             self._hand_conf_var, 0.3, 0.99,
                             "Low ◄──────────── High")

        # Gesture reference table
        ctk.CTkLabel(parent, text="Gesture Reference",
                     font=FONT_SM, text_color=TEXT_SECONDARY).pack(padx=20, pady=(15, 5))

        gestures = [
            ("Index Finger", "Move Cursor"),
            ("Thumb+Index Pinch", "Left Click"),
            ("Index+Middle Pinch", "Right Click"),
            ("Double Pinch", "Double Click"),
            ("Closed Fist", "Drag & Drop"),
            ("Open Palm", "Pause/Resume"),
            ("Swipe Right/Left", "Next/Prev Tab"),
            ("Thumbs Up", "Confirm (Enter)"),
            ("Thumbs Down", "Cancel (Esc)"),
        ]
        for gest, action in gestures:
            row = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=6)
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=gest, font=FONT_XS,
                         text_color=ACCENT_CYAN, width=170, anchor="w").pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(row, text=action, font=FONT_XS,
                         text_color=TEXT_SECONDARY).pack(side="right", padx=10)

    def _build_eye_tab(self, parent):
        self._eye_conf_var = ctk.DoubleVar(value=self._eye_conf)

        self._slider_section(parent, "Eye Detection Confidence",
                             self._eye_conf_var, 0.3, 0.99,
                             "Low ◄──────────── High")

        ctk.CTkLabel(parent, text="Blink Actions",
                     font=FONT_SM, text_color=TEXT_SECONDARY).pack(padx=20, pady=(15, 5))

        blinks = [
            ("Single Blink", "Left Click"),
            ("Double Blink", "Open / Double Click"),
            ("Long Blink (>0.4s)", "Right Click"),
        ]
        for blink, action in blinks:
            row = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=6)
            row.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(row, text=blink, font=FONT_XS,
                         text_color=ACCENT_PURPLE, width=180, anchor="w").pack(side="left", padx=10, pady=5)
            ctk.CTkLabel(row, text=action, font=FONT_XS,
                         text_color=TEXT_SECONDARY).pack(side="right", padx=10)

        ctk.CTkButton(parent, text="🎯 Run Eye Calibration", height=36,
                      fg_color=ACCENT_PURPLE, hover_color="#7C3AED",
                      text_color="white",
                      command=self._run_calibration).pack(padx=20, pady=15)

    def _build_profile_tab(self, parent):
        ctk.CTkLabel(parent, text="Active Profile",
                     font=FONT_SM, text_color=TEXT_SECONDARY).pack(padx=20, pady=15)

        try:
            from database.db_manager import get_all_profiles
            profiles = get_all_profiles()
            names = [p[1] for p in profiles]
        except Exception:
            names = ["Default"]

        self._profile_var = ctk.StringVar(value=names[0] if names else "Default")
        ctk.CTkComboBox(parent, values=names, variable=self._profile_var,
                        fg_color=BG_SURFACE, width=250).pack(padx=20)

        ctk.CTkButton(parent, text="+ New Profile", height=34,
                      fg_color=ACCENT_BLUE, command=self._new_profile
                      ).pack(padx=20, pady=10)

    def _slider_section(self, parent, label: str, var, from_: float, to: float, hint: str):
        frame = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=8)
        frame.pack(fill="x", padx=20, pady=8)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(header, text=label, font=FONT_SM,
                     text_color=TEXT_PRIMARY).pack(side="left")
        val_label = ctk.CTkLabel(header, text=f"{var.get():.2f}",
                                  font=FONT_MONO, text_color=ACCENT_CYAN)
        val_label.pack(side="right")

        slider = ctk.CTkSlider(frame, from_=from_, to=to, variable=var,
                                progress_color=ACCENT_CYAN,
                                button_color=ACCENT_BLUE)
        slider.pack(fill="x", padx=12, pady=(2, 4))

        def on_change(_):
            val_label.configure(text=f"{var.get():.2f}")
        slider.configure(command=on_change)

        ctk.CTkLabel(frame, text=hint, font=FONT_XS,
                     text_color=TEXT_MUTED).pack(padx=12, pady=(0, 8))

    def _test_camera(self):
        idx = self._cam_idx_var.get()
        self._cam_test_label.configure(text="Testing...", text_color=TEXT_MUTED)

        def test():
            import cv2
            cap = cv2.VideoCapture(idx)
            ok = cap.isOpened()
            if ok:
                cap.release()
            msg = f"✓ Camera {idx} OK" if ok else f"✗ Camera {idx} not found"
            color = ACCENT_GREEN if ok else ACCENT_RED
            self.after(0, lambda: self._cam_test_label.configure(text=msg, text_color=color))

        threading.Thread(target=test, daemon=True).start()

    def _run_calibration(self):
        messagebox.showinfo("Eye Calibration",
            "Eye Calibration Wizard\n\n"
            "Follow the dots on screen with your eyes.\n"
            "Keep head still during calibration.\n\n"
            "Calibration will launch when you start Eye Tracking mode.")

    def _new_profile(self):
        dialog = ctk.CTkInputDialog(text="Enter profile name:", title="New Profile")
        name = dialog.get_input()
        if name and name.strip():
            try:
                from database.db_manager import create_profile
                create_profile(name.strip())
                messagebox.showinfo("Profile", f"Profile '{name}' created!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _save(self):
        try:
            from database.db_manager import set_setting
            pid = self._profile_id
            set_setting(pid, "cursor_speed", round(self._cursor_speed_var.get(), 2))
            set_setting(pid, "smoothing", round(self._smoothing_var.get(), 2))
            set_setting(pid, "click_cooldown", round(self._cooldown_var.get(), 2))
            set_setting(pid, "camera_index", int(self._cam_idx_var.get()))
            set_setting(pid, "hand_conf", round(self._hand_conf_var.get(), 2))
            set_setting(pid, "eye_conf", round(self._eye_conf_var.get(), 2))
            messagebox.showinfo("Saved", "Settings saved successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
