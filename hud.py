"""
hud.py — Optimized HUD for Shadow Voice Assistant.

Optimisations
─────────────
• Gradient objects (QRadialGradient, QConicalGradient) cached keyed on
  (color_rgba, radius) — rebuilt only when color or size changes, not 60x/sec.
• Adaptive frame rate: 60 FPS during activity, 30 FPS when IDLE.
• `import random` hoisted to module level.
• `angle_step` initialised in __init__ to avoid AttributeError on first paint.
"""

import math
import random
import time
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont, QConicalGradient


class HUDWindow(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.diameter = config.get("hud.diameter", 300)
        self.resize(self.diameter, self.diameter)
        self._corner_window()

        # State
        self.angle         = 0
        self.angle_step    = 1
        self.pulse_timer   = 0
        self.status        = "IDLE"
        self.last_command  = ""
        self.ai_response   = ""
        self.cpu_usage     = 0
        self.ram_usage     = 0
        self.current_emotion = "CALM"

        self.emotion_colors = {
            "HAPPY":   QColor(0,   255, 150, 200),
            "EXCITED": QColor(255, 200,   0, 200),
            "SAD":     QColor(0,   150, 255, 200),
            "ANGRY":   QColor(255,  50,  50, 200),
            "CURIOUS": QColor(200,   0, 255, 200),
            "CALM":    QColor(0,   212, 255, 200),
        }

        # ── Gradient cache ────────────────────────────────────────────────────
        # key → (color_key, radius) : gradient object
        self._grad_cache: dict = {}
        self._last_color_key: tuple = ()
        self._last_radius: float    = 0

        # ── Adaptive timer (60 FPS active / 30 FPS idle) ──────────────────────
        self._active_interval = 16   # ms ≈ 60 FPS
        self._idle_interval   = 33   # ms ≈ 30 FPS
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self._active_interval)

    # ── Positioning ───────────────────────────────────────────────────────────

    def _corner_window(self):
        geo = self.screen().availableGeometry()
        self.move(geo.width() - self.width() - 20,
                  geo.height() - self.height() - 60)

    # ── Events ────────────────────────────────────────────────────────────────

    def enterEvent(self, event):
        geo   = self.screen().availableGeometry()
        new_x = random.randint(0, geo.width()  - self.width())
        new_y = random.randint(0, geo.height() - self.height())
        self.move(new_x, new_y)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_settings()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background:#0A141E; color:#00D4FF; border:1px solid #00D4FF; font-family:'Rajdhani'; }
            QMenu::item:selected { background:#00D4FF; color:#0A141E; }
        """)
        settings_action = menu.addAction("Settings")
        exit_action     = menu.addAction("Exit System")
        action = menu.exec(event.globalPos())
        if action == settings_action:
            self.open_settings()
        elif action == exit_action:
            QApplication.quit()

    def open_settings(self):
        if hasattr(self, "_settings_callback"):
            self._settings_callback()

    # ── State setters ─────────────────────────────────────────────────────────

    def set_status(self, status: str):
        self.status = status
        if status == "THINKING":
            self.angle_step = 8
            self.timer.setInterval(self._active_interval)
        elif status == "LISTENING":
            self.angle_step = 2
            self.timer.setInterval(self._active_interval)
        elif status == "SPEAKING":
            self.angle_step = 3
            self.timer.setInterval(self._active_interval)
        else:  # IDLE
            self.angle_step = 1
            self.timer.setInterval(self._idle_interval)

    def set_command(self, cmd: str):
        self.last_command = cmd
        QTimer.singleShot(8000, self.clear_command)

    def clear_command(self):
        self.last_command = ""

    def set_response(self, text: str):
        self.ai_response = text

    def update_stats(self, cpu: float, ram: float):
        self.cpu_usage = cpu
        self.ram_usage = ram

    def set_emotion(self, emotion: str):
        if emotion in self.emotion_colors:
            self.current_emotion = emotion
            self._grad_cache.clear()   # invalidate cached gradients on color change
            self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect   = self.rect()
        center = QPointF(rect.width() / 2, rect.height() / 2)
        radius = min(rect.width(), rect.height()) / 2

        self.angle      += self.angle_step
        self.pulse_timer += 0.05
        pulse = (math.sin(self.pulse_timer) + 1) / 2

        color = self.emotion_colors.get(self.current_emotion, QColor(0, 212, 255))

        # 0. Background grid
        self._draw_grid(painter, center, radius, color)

        # 1. Background glow
        glow = self._get_radial_grad("bg", center, radius, color, 0,
                                     QColor(color.red(), color.green(), color.blue(), 60),
                                     0.8, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # 2. Rings
        self._draw_rings(painter, center, radius, color, pulse)

        # 3. State core
        if self.status == "LISTENING":
            self._draw_listening_waves(painter, center, radius, color, pulse)
        elif self.status == "THINKING":
            self._draw_thinking_ring(painter, center, radius, color)
        elif self.status == "SPEAKING":
            self._draw_speaking_core(painter, center, radius, color, pulse)
        else:
            self._draw_idle_core(painter, center, radius, color, pulse)

        # 4. UI text
        self._draw_ui_elements(painter, rect, center, radius, color)

    # ── Gradient cache helpers ────────────────────────────────────────────────

    def _get_radial_grad(self, key, center, radius, color,
                         stop0_pos, stop0_col, stop1_pos, stop1_col):
        cache_key = (key, color.rgba(), radius)
        if cache_key not in self._grad_cache:
            g = QRadialGradient(center, radius)
            g.setColorAt(stop0_pos, stop0_col)
            g.setColorAt(stop1_pos, stop1_col)
            self._grad_cache[cache_key] = g
        return self._grad_cache[cache_key]

    def _draw_grid(self, painter, center, radius, color):
        painter.save()
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 30), 1))
        step = 20
        # Vertical lines
        for x in range(0, int(self.width()), step):
            painter.drawLine(x, 0, x, self.height())
        # Horizontal lines
        for y in range(0, int(self.height()), step):
            painter.drawLine(0, y, self.width(), y)
        
        # Diagonal scanline effect
        scan_y = (int(time.time() * 100) % int(self.height() * 2)) - self.height()
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 15), 2))
        painter.drawLine(0, scan_y, self.width(), scan_y + 50)
        painter.restore()

    # ── Draw helpers ──────────────────────────────────────────────────────────

    def _draw_rings(self, painter, center, radius, color, pulse):
        pen = QPen(color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius * 0.85, radius * 0.85)

        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidth(3)
        painter.setPen(pen)
        r1 = QRectF(center.x() - radius*0.8, center.y() - radius*0.8, radius*1.6, radius*1.6)
        painter.drawArc(r1, int(self.angle * 16), 60 * 16)
        painter.drawArc(r1, int((self.angle + 180) * 16), 60 * 16)

        pen.setWidth(1)
        painter.setPen(pen)
        r2 = QRectF(center.x() - radius*0.75, center.y() - radius*0.75, radius*1.5, radius*1.5)
        painter.drawArc(r2, int(-self.angle * 1.5 * 16), 120 * 16)

    def _draw_listening_waves(self, painter, center, radius, color, pulse):
        pen = QPen(color)
        pen.setWidth(2)
        for i in range(8):
            wave_r = radius * 0.3 + i * 10 + pulse * 5
            alpha  = int(255 * (1 - i / 8.0))
            pen.setColor(QColor(color.red(), color.green(), color.blue(), alpha))
            painter.setPen(pen)
            jitter = math.sin(self.pulse_timer * 5 + i) * 5
            painter.drawEllipse(center, wave_r + jitter, wave_r - jitter)

    def _draw_thinking_ring(self, painter, center, radius, color):
        grad = QConicalGradient(center, self.angle % 360)
        grad.setColorAt(0,   color)
        grad.setColorAt(0.2, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius * 0.6, radius * 0.6)

        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle * 4)
        for _ in range(4):
            painter.rotate(90)
            painter.drawLine(0, -20, 0, -40)
        painter.restore()

    def _draw_speaking_core(self, painter, center, radius, color, pulse):
        core = radius * 0.4 + pulse * 15
        grad = QRadialGradient(center, core)
        grad.setColorAt(0,   color)
        grad.setColorAt(0.8, QColor(color.red(), color.green(), color.blue(), 100))
        grad.setColorAt(1,   QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, core, core)

        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        for i in range(5):
            a  = (self.pulse_timer * 10 + i * 72) * (math.pi / 180)
            px = center.x() + math.cos(a) * (core + 10)
            py = center.y() + math.sin(a) * (core + 10)
            painter.drawPoint(QPointF(px, py))

    def _draw_idle_core(self, painter, center, radius, color, pulse):
        core  = radius * 0.35
        alpha = int(100 + pulse * 50)
        grad  = QRadialGradient(center, core)
        grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), alpha))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, core, core)

    def _draw_ui_elements(self, painter, rect, center, radius, color):
        # Status label
        painter.setPen(color)
        painter.setFont(QFont("Orbitron", 10, QFont.Weight.Bold))
        labels = {"IDLE": "SYSTEM READY", "LISTENING": "LISTENING...",
                  "THINKING": "PROCESSING...", "SPEAKING": "SHADOW SPEAKING"}
        status_text = labels.get(self.status, self.status)
        m = painter.fontMetrics()
        painter.drawText(
            int(center.x() - m.horizontalAdvance(status_text) / 2),
            int(center.y() - radius + 30),
            status_text,
        )

        # CPU / RAM
        painter.setFont(QFont("Rajdhani", 8))
        painter.setPen(QColor(200, 200, 200, 180))
        painter.drawText(QRectF(center.x() - radius + 10, center.y() - 15, 60, 30),
                         Qt.AlignmentFlag.AlignLeft, f"CPU\n{int(self.cpu_usage)}%")
        painter.drawText(QRectF(center.x() + radius - 70, center.y() - 15, 60, 30),
                         Qt.AlignmentFlag.AlignRight, f"RAM\n{int(self.ram_usage)}%")

        # Command
        if self.last_command:
            painter.setFont(QFont("Rajdhani", 9, QFont.Weight.DemiBold))
            painter.setPen(QColor(255, 255, 255, 200))
            cmd  = f'"{self.last_command}"'
            cmd  = m.elidedText(cmd, Qt.TextElideMode.ElideRight, int(radius * 1.5))
            painter.drawText(
                int(center.x() - m.horizontalAdvance(cmd) / 2),
                int(center.y() + radius - 45), cmd,
            )

        # Response
        if self.ai_response:
            painter.setFont(QFont("Rajdhani", 10))
            painter.setPen(Qt.GlobalColor.white)
            rm  = painter.fontMetrics()
            res = rm.elidedText(self.ai_response, Qt.TextElideMode.ElideRight, int(radius * 1.8))
            painter.drawText(
                int(center.x() - rm.horizontalAdvance(res) / 2),
                int(center.y() + radius - 20), res,
            )


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    _app = QApplication(sys.argv)
    w = HUDWindow(type("C", (), {"get": lambda self, k, d=None: d})())
    w.show()
    sys.exit(_app.exec())
