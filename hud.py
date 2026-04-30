"""
hud.py — Futuristic AR HUD for Shadow Assistant.
"""

import sys
import time
import ctypes
import winsound
import threading
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, 
    QLabel, QListWidget, QFrame, QMenu, QApplication,
    QAbstractItemView, QPushButton
)
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QPoint, QPointF, QPropertyAnimation, 
    QEasingCurve, pyqtProperty, QSize, QDateTime, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, 
    QLinearGradient, QAction, QPainterPath
)

class HUDLabel(QLabel):
    """Small uppercase section header."""
    def __init__(self, text, color="#1D9E75"):
        super().__init__(text.upper())
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet(f"color: {color}; letter-spacing: 1px; background: transparent;")

class HUDValue(QLabel):
    """Large metric display."""
    def __init__(self, text="0", color="#e2e8f0"):
        super().__init__(text)
        self.setFont(QFont("Consolas", 20, QFont.Weight.Medium))
        self.setStyleSheet(f"color: {color}; background: transparent;")

class HUDBar(QWidget):
    """Custom painted thin progress bar."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(3)
        self.value = 0.0
        self.color = QColor("#1D9E75")
        self.bg_color = QColor(255, 255, 255, 15)

    def set_value(self, pct: float, color: QColor = None):
        self.value = max(0.0, min(100.0, pct))
        if color:
            self.color = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background track
        p.setBrush(self.bg_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, self.width(), self.height())
        
        # Draw filled part
        p.setBrush(self.color)
        w = int(self.width() * (self.value / 100.0))
        p.drawRect(0, 0, w, self.height())

class HUDPanel(QFrame):
    """Base class for HUD panels with shared aesthetics."""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent; border: none;")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        # Subtle 0.5px bottom border
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

class FaceWidget(QWidget):
    """Animated, expressive AI face."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(100, 100)
        self.emotion = "IDLE"
        self.state = "IDLE"
        self.color = QColor("#1D9E75")
        
        # Eyes and mouth geometry (base values, scaled in paintEvent)
        self.base_eye_size = 10
        self.base_eye_spacing = 30
        self.base_mouth_width = 40
        
        # Animation properties
        self.blink_y = 1.0 # 0.0 to 1.0 (closed to open)
        self.expression_timer = QTimer(self)
        self.expression_timer.timeout.connect(self.update)
        self.expression_timer.start(30)
        
        self.pulse = 0.0
        self.pulse_dir = 1
        
        # Blink timer
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.do_blink)
        self.blink_timer.start(4000)

    def do_blink(self):
        self.blink_anim = QPropertyAnimation(self, b"blink_y_val")
        self.blink_anim.setDuration(150)
        self.blink_anim.setStartValue(1.0)
        self.blink_anim.setEndValue(0.0)
        self.blink_anim.setKeyValueAt(0.5, 0.0)
        self.blink_anim.setEndValue(1.0)
        self.blink_anim.start()

    @pyqtProperty(float)
    def blink_y_val(self): return self.blink_y
    @blink_y_val.setter
    def blink_y_val(self, v): self.blink_y = v

    def set_emotion(self, emotion: str):
        self.emotion = emotion.upper()
        if self.emotion == "ANGRY": self.color = QColor("#FF4B4B")
        elif self.emotion == "EXCITED": self.color = QColor("#7F77DD")
        elif self.emotion == "SAD": self.color = QColor("#4a5568")
        else: self.color = QColor("#1D9E75")
        self.update()

    def set_state(self, state: str):
        self.state = state.upper()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        # Scale factor based on height
        s = min(self.width(), self.height()) / 120.0
        
        # Pulse for Idle/Listening
        if self.state in ["IDLE", "LISTENING"]:
            self.pulse += self.pulse_dir * 0.02
            if self.pulse >= 1.0: self.pulse_dir = -1
            elif self.pulse <= 0.0: self.pulse_dir = 1
        else:
            self.pulse = 0
            
        # Draw subtle glass face boundary
        face_path = QPainterPath()
        fw, fh = 90 * s, 100 * s
        face_path.addRoundedRect(center.x() - fw/2, center.y() - fh/2, fw, fh, 30*s, 30*s)
        p.setPen(QPen(QColor(self.color.red(), self.color.green(), self.color.blue(), 15), 1))
        p.setBrush(QColor(10, 12, 15, 20))
        p.drawPath(face_path)

        # Draw Glow
        glow_size = (60 * s) + (self.pulse * 10 * s)
        grad = QLinearGradient(center.x(), center.y() - glow_size, center.x(), center.y() + glow_size)
        c = self.color
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 20))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(center, int(glow_size), int(glow_size))

        # Draw Eyes
        eye_y = center.y() - (10 * s)
        eye_spacing = self.base_eye_spacing * s
        eye_lx = center.x() - eye_spacing
        eye_rx = center.x() + eye_spacing
        eye_size = self.base_eye_size * s
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.color)
        
        # Adjust eyes based on emotion
        eye_h = eye_size * self.blink_y
        if self.emotion == "HAPPY":
            self.draw_curved_eye(p, QPointF(float(eye_lx), float(eye_y)), True, eye_size)
            self.draw_curved_eye(p, QPointF(float(eye_rx), float(eye_y)), True, eye_size)
        elif self.emotion == "ANGRY":
            self.draw_slanted_eye(p, QPointF(float(eye_lx), float(eye_y)), True, eye_size)
            self.draw_slanted_eye(p, QPointF(float(eye_rx), float(eye_y)), False, eye_size)
        elif self.emotion == "SAD":
            self.draw_slanted_eye(p, QPointF(float(eye_lx), float(eye_y)), False, eye_size)
            self.draw_slanted_eye(p, QPointF(float(eye_rx), float(eye_y)), True, eye_size)
        elif self.state == "THINKING":
            angle = (time.time() * 500) % 360
            self.draw_spinning_eye(p, QPointF(float(eye_lx), float(eye_y)), angle, eye_size)
            self.draw_spinning_eye(p, QPointF(float(eye_rx), float(eye_y)), angle, eye_size)
        else:
            for x_pos in [eye_lx, eye_rx]:
                eye_path = QPainterPath()
                ew, eh = eye_size * 1.2, eye_h
                eye_path.addEllipse(QPointF(float(x_pos), float(eye_y)), float(ew), float(eh))
                p.fillPath(eye_path, self.color)
                # Inner pupil
                p.setBrush(QColor(255, 255, 255, 80))
                p.drawEllipse(QPointF(float(x_pos), float(eye_y - 2*s)), 2.0*s, 2.0*s)
                p.setBrush(self.color)

        # Draw Mouth
        mouth_y = center.y() + (15 * s)
        p.setPen(QPen(self.color, 2*s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        
        path = QPainterPath()
        mw = self.base_mouth_width * s / 2
        if self.emotion == "HAPPY":
            path.moveTo(center.x() - mw, mouth_y)
            path.quadTo(center.x(), mouth_y + (10*s), center.x() + mw, mouth_y)
        elif self.emotion == "SAD":
            path.moveTo(center.x() - mw, mouth_y + (5*s))
            path.quadTo(center.x(), mouth_y - (5*s), center.x() + mw, mouth_y + (5*s))
        elif self.emotion == "ANGRY":
            p.drawLine(QPointF(center.x() - mw*0.8, mouth_y + (2*s)), QPointF(center.x() + mw*0.8, mouth_y + (2*s)))
        elif self.emotion == "EXCITED":
            path.moveTo(center.x() - mw, mouth_y)
            path.quadTo(center.x(), mouth_y + (15*s), center.x() + mw, mouth_y)
            p.setBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 40))
            path.closeSubpath()
        elif self.emotion == "CURIOUS":
            path.moveTo(center.x() - mw*0.7, mouth_y + (2*s))
            path.quadTo(center.x() + (5*s), mouth_y + (5*s), center.x() + mw*0.7, mouth_y)
        else: # CALM / IDLE
            p.drawLine(QPointF(center.x() - mw*0.6, mouth_y + (2*s)), QPointF(center.x() + mw*0.6, mouth_y + (2*s)))
            
        p.drawPath(path)

    def draw_curved_eye(self, p, pos, up, size):
        path = QPainterPath()
        w, h = size*1.25, size*0.75
        if up:
            path.moveTo(pos.x() - w/2, pos.y() + h/2)
            path.quadTo(pos.x(), pos.y() - h/2, pos.x() + w/2, pos.y() + h/2)
        else:
            path.moveTo(pos.x() - w/2, pos.y() - h/2)
            path.quadTo(pos.x(), pos.y() + h/2, pos.x() + w/2, pos.y() - h/2)
        p.drawPath(path)

    def draw_slanted_eye(self, p, pos, inner_up, size):
        points = []
        w, h = size*1.25, size*0.75
        if inner_up: # / \
            points = [QPointF(pos.x()-w/2, pos.y()+h/2), QPointF(pos.x()+w/2, pos.y()-h/2)]
        else: # \ /
            points = [QPointF(pos.x()-w/2, pos.y()-h/2), QPointF(pos.x()+w/2, pos.y()+h/2)]
        p.setPen(QPen(self.color, size*0.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(points[0], points[1])

    def draw_spinning_eye(self, p, pos, angle, size):
        p.setPen(QPen(self.color, size*0.2))
        p.drawEllipse(pos, float(size), float(size))
        import math
        rad = math.radians(angle)
        ex = pos.x() + math.cos(rad) * (size - 2)
        ey = pos.y() + math.sin(rad) * (size - 2)
        p.setBrush(self.color)
        p.drawEllipse(QPointF(ex, ey), 2.0, 2.0)

class ShadowHUD(QWidget):
    reminder_signal = pyqtSignal(str) # For thread-safe alarms
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # Window Properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Windows-specific: WS_EX_NOACTIVATE to prevent focus stealing
        if sys.platform == "win32":
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_NOACTIVATE
            )

        # Initial Size & Position — narrower, taller to fit stacked layout
        self.default_width = config.get("hud_width", 300)
        self.default_height = config.get("hud_height", 360)
        self.resize(self.default_width, self.default_height)
        self.setMinimumSize(240, 280)
        self.setMaximumSize(500, 700)
        
        self.restore_position()
        self.setWindowOpacity(1.0)
        print(f"[HUD] Initialized at {self.pos()} with size {self.size()}")

        # State Variables
        self.scanline_y = 0
        self.dragging = False
        self.resizing = False
        self.drag_pos = QPoint()
        self.is_listening = False
        self.is_processing = False
        self.uptime_start = time.time()
        self.status_indicators = {}

        # Animation timers
        self.scanline_timer = QTimer(self)
        self.scanline_timer.timeout.connect(self.update_scanline)
        self.scanline_timer.start(30)

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_timer.start(100)
        self.pulse_opacity = 1.0
        self.pulse_dir = -1

        # UI Layout
        self.init_ui()
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        # Reminder refresh timer (every 10 seconds is enough)
        self.rem_timer = QTimer(self)
        self.rem_timer.timeout.connect(self.refresh_reminders)
        self.rem_timer.start(10000)
        
        # Connect reminder signal for thread-safety
        self.reminder_signal.connect(self.trigger_alarm)

    def restore_position(self):
        x = self.config.get("hud_x", -1)
        y = self.config.get("hud_y", -1)
        w = self.config.get("hud_width", self.default_width)
        h = self.config.get("hud_height", self.default_height)
        
        self.resize(w, h)
        
        if x == -1 or y == -1:
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 60)
        else:
            self.move(x, y)

    def init_ui(self):
        # Single-column vertical layout: top bar → face → transcript
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(6)

        # ── Row 0: Top Bar ──────────────────────────────────────────────
        top_bar = HUDPanel()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 0, 10, 0)
        
        self.version_lbl = QLabel("SHADOW v2.1")
        self.version_lbl.setFont(QFont("Consolas", 10))
        self.version_lbl.setStyleSheet("color: #2d3748;")
        
        self.clock_lbl = QLabel("00:00:00")
        self.clock_lbl.setFont(QFont("Consolas", 10))
        self.clock_lbl.setStyleSheet("color: #4a5568;")
        self.clock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.mode_lbl = QLabel("● IDLE")
        self.mode_lbl.setFont(QFont("Consolas", 10))
        self.mode_lbl.setStyleSheet("color: #4a5568;")
        self.mode_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        top_layout.addWidget(self.version_lbl)
        top_layout.addStretch()
        top_layout.addWidget(self.clock_lbl)
        top_layout.addStretch()
        top_layout.addWidget(self.mode_lbl)
        
        self.main_layout.addWidget(top_bar)

        # ── Row 1: Face + buttons (centred) ────────────────────────────
        face_panel = HUDPanel()
        face_v = QVBoxLayout(face_panel)
        face_v.setContentsMargins(5, 4, 5, 4)
        face_v.setSpacing(4)

        self.face = FaceWidget()
        self.face.setFixedSize(140, 140)
        face_v.addWidget(self.face, 0, alignment=Qt.AlignmentFlag.AlignHCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        hide_btn = QPushButton("HIDE")
        hide_btn.setFont(QFont("Consolas", 7))
        hide_btn.setStyleSheet(
            "color: #4a5568; padding: 4px;"
            "background: rgba(255,255,255,5);"
            "border: 1px solid rgba(255,255,255,10);"
        )
        hide_btn.clicked.connect(self.hide_hud)
        btn_layout.addWidget(hide_btn)
        
        mute_btn = QPushButton("MUTE")
        mute_btn.setFont(QFont("Consolas", 7))
        mute_btn.setStyleSheet(
            "color: #4a5568; padding: 4px;"
            "background: rgba(255,255,255,5);"
            "border: 1px solid rgba(255,255,255,10);"
        )
        mute_btn.clicked.connect(self.toggle_mute)
        btn_layout.addWidget(mute_btn)
        self.mute_btn = mute_btn

        face_v.addLayout(btn_layout)
        self.main_layout.addWidget(face_panel)

        # ── Row 2: Live Transcript (below the face) ────────────────────
        trans_panel = HUDPanel()
        trans_v = QVBoxLayout(trans_panel)
        trans_v.setContentsMargins(8, 4, 8, 4)
        trans_v.setSpacing(2)

        trans_header = QHBoxLayout()
        self.pulse_dot = QLabel("●")
        self.pulse_dot.setStyleSheet("color: #1D9E75;")
        trans_header.addWidget(self.pulse_dot)
        trans_header.addWidget(HUDLabel("LIVE TRANSCRIPT"))
        trans_header.addStretch()
        trans_v.addLayout(trans_header)
        
        self.transcript_lbl = QLabel("Awaiting input...")
        self.transcript_lbl.setWordWrap(True)
        self.transcript_lbl.setFont(QFont("Consolas", 10))
        self.transcript_lbl.setStyleSheet("color: #a0aec0; padding: 4px 2px;")
        self.transcript_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.transcript_lbl.setMinimumHeight(60)
        trans_v.addWidget(self.transcript_lbl)

        self.main_layout.addWidget(trans_panel)

        # ── Row 3: Reminders List (NEW) ────────────────────────────────
        self.rem_panel = HUDPanel()
        rem_v = QVBoxLayout(self.rem_panel)
        rem_v.setContentsMargins(8, 4, 8, 4)
        rem_v.setSpacing(2)
        
        rem_header = QHBoxLayout()
        rem_header.addWidget(HUDLabel("UPCOMING TASKS", color="#BA7517"))
        rem_header.addStretch()
        rem_v.addLayout(rem_header)
        
        self.reminders_container = QVBoxLayout()
        self.reminders_container.setSpacing(2)
        rem_v.addLayout(self.reminders_container)
        
        self.no_rem_lbl = QLabel("No active tasks.")
        self.no_rem_lbl.setFont(QFont("Consolas", 8))
        self.no_rem_lbl.setStyleSheet("color: #4a5568; font-style: italic;")
        self.reminders_container.addWidget(self.no_rem_lbl)
        
        self.main_layout.addWidget(self.rem_panel)

        self.main_layout.setStretch(0, 0)  # top bar fixed
        self.main_layout.setStretch(1, 0)  # face fixed
        self.main_layout.setStretch(2, 2)  # transcript expands
        self.main_layout.setStretch(3, 1)  # reminders fixed/small

    def add_status_indicator(self, key, value, state):
        return QLabel()

    # --- Public Methods ---

    def update_transcript(self, text: str):
        import re
        highlighted = re.sub(
            r"(shadow)",
            r'<span style="color:#e2e8f0;"><b>\1</b></span>',
            text, flags=re.IGNORECASE
        )
        self.transcript_lbl.setText(highlighted)

    def add_log_entry(self, cmd: str, result: str):
        pass

    def set_status(self, key: str, value: str, state: str = "ok"):
        pass

    def set_listening(self, active: bool):
        self.is_listening = active
        if active:
            self.mode_lbl.setText("● LISTENING")
            self.mode_lbl.setStyleSheet("color: #1D9E75;")
            self.face.set_state("LISTENING")
        else:
            self.mode_lbl.setText("● IDLE")
            self.mode_lbl.setStyleSheet("color: #4a5568;")
            self.face.set_state("IDLE")

    def set_processing(self, active: bool):
        self.is_processing = active
        if active:
            self.mode_lbl.setText("● PROCESSING")
            self.mode_lbl.setStyleSheet("color: #BA7517;")
            self.face.set_state("THINKING")
        else:
            self.set_listening(self.is_listening)

    def set_emotion(self, emotion: str):
        if hasattr(self, "face"):
            self.face.set_emotion(emotion)

    def show_hud(self):
        print(f"[HUD] Showing HUD (Opacity: {self.config.get('hud_opacity', 0.92)})")
        self.show()
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(self.config.get("hud_opacity", 0.92))
        self.fade_anim.start()

    def hide_hud(self):
        print("[HUD] Hiding HUD")
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self.hide)
        self.fade_anim.start()

    def toggle_mute(self):
        if hasattr(self, "_mute_callback"):
            is_enabled = self._mute_callback()
            self.mute_btn.setText("UNMUTE" if not is_enabled else "MUTE")
            self.mute_btn.setStyleSheet(
                f"color: {'#FF4B4B' if not is_enabled else '#4a5568'};"
                "background: rgba(255,255,255,5);"
                "border: 1px solid rgba(255,255,255,10);"
            )

    def trigger_alarm(self, label: str):
        """Visual and audible alert for a firing reminder."""
        self.show_hud() # Ensure it's visible
        self.update_transcript(f"<span style='color:#FF4B4B;'><b>[ALARM]</b></span> {label}")
        self.set_emotion("EXCITED")
        
        # Play beep sound 3 times in background
        def _beep():
            try:
                for _ in range(3):
                    winsound.Beep(1000, 400) # 1000Hz, 400ms
                    time.sleep(0.2)
            except: pass
        threading.Thread(target=_beep, daemon=True).start()

        # Flash the background
        self.flash_anim = QPropertyAnimation(self, b"windowOpacity")
        self.flash_anim.setDuration(300)
        self.flash_anim.setStartValue(self.windowOpacity())
        self.flash_anim.setEndValue(1.0)
        self.flash_anim.setKeyValueAt(0.5, 0.5)
        self.flash_anim.setEndValue(self.config.get("hud_opacity", 0.92))
        self.flash_anim.start()
        # Force a refresh
        self.refresh_reminders()

    def refresh_reminders(self):
        """Update the reminders list from TimerCommands."""
        try:
            from commands.extra_cmds import TimerCommands
            reminders = TimerCommands.get_active_data()
            
            # Clear old dynamic widgets
            while self.reminders_container.count():
                child = self.reminders_container.takeAt(0)
                widget = child.widget()
                if widget and widget != self.no_rem_lbl:
                    widget.deleteLater()
            
            if not reminders:
                if self.no_rem_lbl.parent() is None:
                    self.reminders_container.addWidget(self.no_rem_lbl)
                self.no_rem_lbl.show()
                return
            
            self.no_rem_lbl.hide()
            for r in reminders[:3]: # Show top 3
                row = QWidget()
                row_l = QHBoxLayout(row)
                row_l.setContentsMargins(0, 0, 0, 0)
                
                lbl = QLabel(f"• {r['label'][:20]}")
                lbl.setFont(QFont("Consolas", 9))
                lbl.setStyleSheet("color: #e2e8f0;")
                
                time_lbl = QLabel(r['time'])
                time_lbl.setFont(QFont("Consolas", 8))
                time_lbl.setStyleSheet("color: #BA7517;")
                time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                
                row_l.addWidget(lbl)
                row_l.addStretch()
                row_l.addWidget(time_lbl)
                self.reminders_container.addWidget(row)
        except Exception as e:
            print(f"[HUD] Refresh rem error: {e}")

    # --- Timers & Stats ---

    def update_scanline(self):
        if not self.config.get("hud_scanline", True): return
        self.scanline_y += 2
        if self.scanline_y > self.height():
            self.scanline_y = 0
        self.update()

    def update_pulse(self):
        if not self.is_listening:
            self.pulse_dot.setWindowOpacity(1.0)
            return
        self.pulse_opacity += self.pulse_dir * 0.1
        if self.pulse_opacity <= 0.3:
            self.pulse_dir = 1
        elif self.pulse_opacity >= 1.0:
            self.pulse_dir = -1
        self.pulse_dot.setStyleSheet(
            f"color: rgba(29, 158, 117, {int(self.pulse_opacity*255)});"
        )

    def update_clock(self):
        self.clock_lbl.setText(QDateTime.currentDateTime().toString("HH:mm:ss"))

    # --- Events ---

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        p.setBrush(QColor(10, 12, 15, 210))
        p.setPen(QPen(QColor(29, 158, 117, 60), 1))
        p.drawRect(0, 0, self.width()-1, self.height()-1)
        
        # Corner Accents
        if self.config.get("hud_corners", True):
            p.setPen(QPen(QColor(29, 158, 117, 180), 2))
            l = 20
            p.drawLine(0, 0, l, 0); p.drawLine(0, 0, 0, l)
            p.drawLine(self.width(), 0, self.width()-l, 0); p.drawLine(self.width(), 0, self.width(), l)
            p.drawLine(0, self.height(), l, self.height()); p.drawLine(0, self.height(), 0, self.height()-l)
            p.drawLine(self.width(), self.height(), self.width()-l, self.height()); p.drawLine(self.width(), self.height(), self.width(), self.height()-l)

        # Scan Line
        if self.config.get("hud_scanline", True):
            grad = QLinearGradient(0, self.scanline_y - 10, 0, self.scanline_y + 10)
            grad.setColorAt(0, QColor(0,0,0,0))
            grad.setColorAt(0.5, QColor(29, 158, 117, 40))
            grad.setColorAt(1, QColor(0,0,0,0))
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(0, self.scanline_y - 10, self.width(), 20)
            
            p.setPen(QPen(QColor(29, 158, 117, 100), 1))
            p.drawLine(0, self.scanline_y, self.width(), self.scanline_y)

        # Resize handle indicator (bottom-right)
        p.setPen(QPen(QColor(29, 158, 117, 100), 1))
        p.drawLine(self.width()-10, self.height(), self.width(), self.height()-10)
        p.drawLine(self.width()-5, self.height(), self.width(), self.height()-5)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().x() > self.width() - 20 and event.pos().y() > self.height() - 20:
                self.resizing = True
            else:
                self.dragging = True
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            self.save_config()
        elif self.resizing:
            new_size = event.pos()
            self.resize(max(self.minimumWidth(), new_size.x()), 
                        max(self.minimumHeight(), new_size.y()))
            self.save_config()

    def enterEvent(self, event):
        if not self.config.get("hud_dodge_enabled", True): return
        if self.dragging or self.resizing: return
        
        screen = QApplication.primaryScreen().geometry()
        margin = 20
        
        if self.x() > (screen.width() / 2):
            target_x = margin
        else:
            target_x = screen.width() - self.width() - margin
            
        self.pos_anim = QPropertyAnimation(self, b"pos")
        self.pos_anim.setDuration(400)
        self.pos_anim.setStartValue(self.pos())
        self.pos_anim.setEndValue(QPoint(int(target_x), self.y()))
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.pos_anim.start()
        
    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False

    def save_config(self):
        self.config.set("hud_x", self.x())
        self.config.set("hud_y", self.y())
        self.config.set("hud_width", self.width())
        self.config.set("hud_height", self.height())

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #0a0c0f; color: #1D9E75; border: 1px solid #1D9E7566; }
            QMenu::item:selected { background: #1D9E7522; }
        """)
        
        hide_act = QAction("Hide HUD", self)
        hide_act.triggered.connect(self.hide_hud)
        
        settings_act = QAction("Settings", self)
        if hasattr(self, "_settings_callback"):
            settings_act.triggered.connect(self._settings_callback)
        
        reset_act = QAction("Reset Position", self)
        reset_act.triggered.connect(self.reset_position)
        
        menu.addAction(hide_act)
        menu.addAction(settings_act)
        menu.addSeparator()
        menu.addAction(reset_act)
        menu.exec(pos)

    def reset_position(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.default_width - 20, screen.height() - self.default_height - 60)
        self.resize(self.default_width, self.default_height)
        self.save_config()

if __name__ == "__main__":
    from config_manager import config_manager
    app = QApplication(sys.argv)
    hud = ShadowHUD(config_manager)
    hud.show_hud()
    sys.exit(app.exec())