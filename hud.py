"""
hud.py — Futuristic AR HUD for Shadow Assistant.
"""

import sys
import time
import psutil
import ctypes
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, 
    QLabel, QListWidget, QFrame, QMenu, QApplication,
    QAbstractItemView, QPushButton
)
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QPoint, QPropertyAnimation, 
    QEasingCurve, pyqtProperty, QSize, QDateTime
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, 
    QLinearGradient, QAction
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

class ShadowHUD(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # Window Properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
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

        # Initial Size & Position
        self.default_width = config.get("hud_width", 420)
        self.default_height = config.get("hud_height", 320)
        self.resize(self.default_width, self.default_height)
        self.setMinimumSize(320, 240)
        self.setMaximumSize(800, 600)
        
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
        self.status_indicators = {} # key -> (dot_color, value_label)

        # Animation timers
        self.scanline_timer = QTimer(self)
        self.scanline_timer.timeout.connect(self.update_scanline)
        self.scanline_timer.start(30) # ~33 fps

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_timer.start(100)
        self.pulse_opacity = 1.0
        self.pulse_dir = -1

        # UI Layout
        self.init_ui()
        
        # Stat update timers
        self.cpu_timer = QTimer(self)
        self.cpu_timer.timeout.connect(self.update_cpu)
        self.cpu_timer.start(1500)

        self.mem_timer = QTimer(self)
        self.mem_timer.timeout.connect(self.update_ram_net)
        self.mem_timer.start(2000)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock_uptime)
        self.clock_timer.start(1000)

    def restore_position(self):
        x = self.config.get("hud_x", -1)
        y = self.config.get("hud_y", -1)
        w = self.config.get("hud_width", self.default_width)
        h = self.config.get("hud_height", self.default_height)
        
        self.resize(w, h)
        
        if x == -1 or y == -1:
            # Default to bottom-right corner
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 60)
        else:
            self.move(x, y)

    def init_ui(self):
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(1)

        # Row 0: Top Bar
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
        
        self.main_layout.addWidget(top_bar, 0, 0, 1, 2)

        # Row 1: Stat Panels
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(1)
        
        # CPU
        cpu_panel = HUDPanel()
        cpu_v = QVBoxLayout(cpu_panel)
        cpu_v.addWidget(HUDLabel("CPU"))
        self.cpu_val = HUDValue("0%")
        cpu_v.addWidget(self.cpu_val)
        self.cpu_sub = QLabel("0 cores · 0.0 GHz")
        self.cpu_sub.setFont(QFont("Consolas", 8))
        self.cpu_sub.setStyleSheet("color: #4a5568;")
        cpu_v.addWidget(self.cpu_sub)
        self.cpu_bar = HUDBar()
        cpu_v.addWidget(self.cpu_bar)
        stats_layout.addWidget(cpu_panel)
        
        # RAM
        ram_panel = HUDPanel()
        ram_v = QVBoxLayout(ram_panel)
        ram_v.addWidget(HUDLabel("RAM", "#7F77DD"))
        self.ram_val = HUDValue("0.0GB")
        ram_v.addWidget(self.ram_val)
        self.ram_sub = QLabel("of 0GB used")
        self.ram_sub.setFont(QFont("Consolas", 8))
        self.ram_sub.setStyleSheet("color: #4a5568;")
        ram_v.addWidget(self.ram_sub)
        self.ram_bar = HUDBar()
        self.ram_bar.color = QColor("#7F77DD")
        ram_v.addWidget(self.ram_bar)
        stats_layout.addWidget(ram_panel)
        
        # NET
        net_panel = HUDPanel()
        net_v = QVBoxLayout(net_panel)
        net_v.addWidget(HUDLabel("NET"))
        self.net_val = HUDValue("0.0MB/s")
        net_v.addWidget(self.net_val)
        self.net_sub = QLabel("↑ 0.0 · ↓ 0.0 MB/s")
        self.net_sub.setFont(QFont("Consolas", 8))
        self.net_sub.setStyleSheet("color: #4a5568;")
        net_v.addWidget(self.net_sub)
        self.net_bar = HUDBar()
        net_v.addWidget(self.net_bar)
        stats_layout.addWidget(net_panel)
        
        self.main_layout.addWidget(stats_widget, 1, 0, 1, 2)

        # Row 2: Transcript Panel
        trans_panel = HUDPanel()
        trans_v = QVBoxLayout(trans_panel)
        trans_header = QHBoxLayout()
        self.pulse_dot = QLabel("●")
        self.pulse_dot.setStyleSheet("color: #1D9E75;")
        trans_header.addWidget(self.pulse_dot)
        trans_header.addWidget(HUDLabel("LIVE TRANSCRIPT"))
        trans_header.addStretch()
        trans_v.addLayout(trans_header)
        
        self.transcript_lbl = QLabel("Awaiting input...")
        self.transcript_lbl.setWordWrap(True)
        self.transcript_lbl.setFont(QFont("Consolas", 12))
        self.transcript_lbl.setStyleSheet("color: #a0aec0;")
        trans_v.addWidget(self.transcript_lbl)
        trans_panel.setMinimumHeight(70)
        self.main_layout.addWidget(trans_panel, 2, 0, 1, 2)

        # Row 3: Command Log
        log_panel = HUDPanel()
        log_v = QVBoxLayout(log_panel)
        log_v.addWidget(HUDLabel("COMMAND LOG", "#7F77DD"))
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #a0aec0; }
            QListWidget::item { padding: 2px; }
        """)
        self.log_list.setFont(QFont("Consolas", 11))
        self.log_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.log_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        log_v.addWidget(self.log_list)
        log_panel.setMinimumHeight(60)
        self.main_layout.addWidget(log_panel, 3, 0, 1, 2)

        # Right Column (Column 2): Status Indicators
        status_panel = HUDPanel()
        status_panel.setFixedWidth(120)
        self.status_v = QVBoxLayout(status_panel)
        self.status_v.setContentsMargins(10, 10, 10, 10)
        self.status_v.setSpacing(8)
        
        self.add_status_indicator("STT", "cloud", "ok")
        self.add_status_indicator("LLM", "gpt-4o", "ok")
        self.add_status_indicator("TTS", "kokoro", "ok")
        self.add_status_indicator("MEM", "0 facts", "ok")
        self.add_status_indicator("WAKE", "ON", "ok")
        self.uptime_lbl = self.add_status_indicator("UPTIME", "00:00:00", "ok")
        
        self.status_v.addStretch()
        
        hide_btn = QPushButton("HIDE")
        hide_btn.setFont(QFont("Consolas", 8))
        hide_btn.setStyleSheet("color: #4a5568; background: rgba(255,255,255,5); border: 1px solid rgba(255,255,255,10);")
        hide_btn.clicked.connect(self.hide_hud)
        self.status_v.addWidget(hide_btn)
        
        mute_btn = QPushButton("MUTE")
        mute_btn.setFont(QFont("Consolas", 8))
        mute_btn.setStyleSheet("color: #4a5568; background: rgba(255,255,255,5); border: 1px solid rgba(255,255,255,10);")
        mute_btn.clicked.connect(self.toggle_mute)
        self.status_v.addWidget(mute_btn)
        self.mute_btn = mute_btn
        
        self.main_layout.addWidget(status_panel, 1, 2, 3, 1)

    def add_status_indicator(self, key, value, state):
        row = QHBoxLayout()
        dot = QLabel("●")
        color = "#1D9E75" if state == "ok" else "#BA7517" if state == "warn" else "#FF4B4B"
        dot.setStyleSheet(f"color: {color}; font-size: 8px;")
        
        lbl = QLabel(key)
        lbl.setFont(QFont("Consolas", 8))
        lbl.setStyleSheet("color: #4a5568;")
        
        val = QLabel(value)
        val.setFont(QFont("Consolas", 8))
        val.setStyleSheet("color: #a0aec0;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        row.addWidget(dot)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        self.status_v.addLayout(row)
        self.status_indicators[key] = (dot, val)
        return val

    # --- Public Methods ---

    def update_transcript(self, text: str):
        # Highlight "shadow" (case-insensitive) in white bold (#e2e8f0)
        import re
        highlighted = re.sub(r"(shadow)", r'<span style="color:#e2e8f0;"><b>\1</b></span>', text, flags=re.IGNORECASE)
        self.transcript_lbl.setText(highlighted)

    def add_log_entry(self, cmd: str, result: str):
        now = QDateTime.currentDateTime().toString("HH:mm:ss")
        # Format: {HH:MM:SS} {command} → {result}
        # Colors: time=#2d3748, cmd=#7F77DD, result=#4a5568
        entry_html = f'<span style="color:#2d3748;">{now}</span>  <span style="color:#7F77DD;">{cmd}</span>  <span style="color:#4a5568;">→  {result}</span>'
        
        item_widget = QLabel(entry_html)
        item_widget.setFont(QFont("Consolas", 11))
        item_widget.setStyleSheet("background: transparent;")
        
        from PyQt6.QtWidgets import QListWidgetItem
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(self.log_list.width(), 25))
        self.log_list.insertItem(0, list_item)
        self.log_list.setItemWidget(list_item, item_widget)
        
        # Trim to last 6
        while self.log_list.count() > 6:
            self.log_list.takeItem(self.log_list.count() - 1)
            
        # Simple fade-in effect for the new item
        self.fade_list_item(item_widget)

    def fade_list_item(self, widget):
        # Using windowOpacity on a child widget won't work, so we use QGraphicsOpacityEffect
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        opacity_effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)
        
        anim = QPropertyAnimation(opacity_effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        # Keep a reference to prevent GC
        if not hasattr(self, "_anims"): self._anims = []
        self._anims.append((anim, opacity_effect))
        anim.finished.connect(lambda: self._anims.remove((anim, opacity_effect)) if (anim, opacity_effect) in self._anims else None)

    def set_status(self, key: str, value: str, state: str = "ok"):
        if key in self.status_indicators:
            dot, val_lbl = self.status_indicators[key]
            color = "#1D9E75" if state == "ok" else "#BA7517" if state == "warn" else "#FF4B4B"
            dot.setStyleSheet(f"color: {color}; font-size: 8px;")
            val_lbl.setText(str(value))

    def set_listening(self, active: bool):
        self.is_listening = active
        if active:
            self.mode_lbl.setText("● LISTENING")
            self.mode_lbl.setStyleSheet("color: #1D9E75;")
        else:
            self.mode_lbl.setText("● IDLE")
            self.mode_lbl.setStyleSheet("color: #4a5568;")

    def set_processing(self, active: bool):
        self.is_processing = active
        if active:
            self.mode_lbl.setText("● PROCESSING")
            self.mode_lbl.setStyleSheet("color: #BA7517;")
        else:
            self.set_listening(self.is_listening)

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
            self.set_status("WAKE", "ON" if is_enabled else "OFF", "ok" if is_enabled else "warn")
            self.mute_btn.setText("UNMUTE" if not is_enabled else "MUTE")
            self.mute_btn.setStyleSheet(f"color: {'#FF4B4B' if not is_enabled else '#4a5568'}; background: rgba(255,255,255,5); border: 1px solid rgba(255,255,255,10);")

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
        self.pulse_dot.setStyleSheet(f"color: rgba(29, 158, 117, {int(self.pulse_opacity*255)});")

    def update_cpu(self):
        try:
            pct = psutil.cpu_percent(interval=None)
            self.cpu_val.setText(f"{int(pct)}%")
            self.cpu_bar.set_value(pct, QColor("#BA7517") if pct >= 70 else QColor("#1D9E75"))
            cores = psutil.cpu_count()
            freq = psutil.cpu_freq().current / 1000.0 if psutil.cpu_freq() else 0.0
            self.cpu_sub.setText(f"{cores} cores · {freq:.1f} GHz")
        except:
            self.cpu_val.setText("n/a")

    def update_ram_net(self):
        try:
            # Update MEM facts count
            import json
            import os
            mem_file = os.path.join(os.path.dirname(__file__), "memory.json")
            if os.path.exists(mem_file):
                with open(mem_file, "r", encoding="utf-8") as f:
                    mem_data = json.load(f)
                    facts_count = len(mem_data.get("notes", []))
                    self.set_status("MEM", f"{facts_count} facts", "ok")
            
            mem = psutil.virtual_memory()
            used_gb = mem.used / 1e9
            total_gb = mem.total / 1e9
            self.ram_val.setText(f"{used_gb:.1f}GB")
            self.ram_sub.setText(f"of {int(total_gb)}GB used")
            self.ram_bar.set_value(mem.percent)
            
            # Net
            net1 = psutil.net_io_counters()
            time.sleep(0.1)
            net2 = psutil.net_io_counters()
            up = (net2.bytes_sent - net1.bytes_sent) / (1024 * 1024 * 0.1)
            down = (net2.bytes_recv - net1.bytes_recv) / (1024 * 1024 * 0.1)
            self.net_val.setText(f"{up+down:.1f}MB/s")
            self.net_sub.setText(f"↑ {up:.1f} · ↓ {down:.1f} MB/s")
            self.net_bar.set_value(min(100, (up+down)*10)) # scaling
        except:
            self.ram_val.setText("n/a")
            self.net_val.setText("n/a")

    def update_clock_uptime(self):
        self.clock_lbl.setText(QDateTime.currentDateTime().toString("HH:mm:ss"))
        uptime_sec = int(time.time() - self.uptime_start)
        h = uptime_sec // 3600
        m = (uptime_sec % 3600) // 60
        s = uptime_sec % 60
        self.uptime_lbl.setText(f"{h:02}:{m:02}:{s:02}")

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
            # Top-left
            p.drawLine(0, 0, l, 0); p.drawLine(0, 0, 0, l)
            # Top-right
            p.drawLine(self.width(), 0, self.width()-l, 0); p.drawLine(self.width(), 0, self.width(), l)
            # Bottom-left
            p.drawLine(0, self.height(), l, self.height()); p.drawLine(0, self.height(), 0, self.height()-l)
            # Bottom-right
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
            # Check for resize handle (bottom-right 20x20 area)
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
        # Dodge to the other side of the screen on hover
        if self.dragging or self.resizing: return
        
        screen = QApplication.primaryScreen().geometry()
        margin = 20
        
        # Calculate target X (swap sides)
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
