"""
hud.py — Nova-style HUD for Shadow Voice Assistant.
"""

import math
import random
import time
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QFont,
    QConicalGradient, QBrush, QPixmap, QLinearGradient
)

# Nova color palette
_GREEN       = QColor(0, 255, 157, 220)
_GREEN_DIM   = QColor(0, 255, 157, 60)
_GREEN_GLOW  = QColor(0, 255, 100, 25)
_WHITE_SOFT  = QColor(255, 255, 255, 180)

_EMOTION_PALETTE = {
    "HAPPY":   QColor(0,   255, 157, 220),
    "EXCITED": QColor(255, 220,   0, 220),
    "SAD":     QColor(30,  120, 255, 220),
    "ANGRY":   QColor(255,  50,  50, 220),
    "CURIOUS": QColor(180,   0, 255, 220),
    "CALM":    QColor(0,   255, 157, 220),
}

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

        self.diameter = config.get("hud.diameter", 340)
        self.resize(self.diameter, self.diameter)
        self._corner_window()

        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(450)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_anim.finished.connect(self._on_fade_finished)

        self.angle           = 0.0
        self.angle_step      = 0.4
        self.pulse_timer     = 0.0
        self.ripple_phases   = [0.0, 0.8, 1.6, 2.4]
        self.eq_bars         = [0.3] * 7
        self.status          = "IDLE"
        self.last_command    = ""
        self.ai_response     = ""
        self.cpu_usage       = 0
        self.ram_usage       = 0
        self.current_emotion = "CALM"

        self._grid_pixmap: QPixmap | None = None
        self._grid_size: tuple = (0, 0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50) # Start with idle interval

    def _on_fade_finished(self):
        if self.windowOpacity() < 0.1: self.hide()

    def _corner_window(self):
        geo = self.screen().availableGeometry()
        self.move(geo.width() - self.width() - 24, geo.height() - self.height() - 60)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._grid_pixmap = None

    def enterEvent(self, event):
        geo   = self.screen().availableGeometry()
        self.move(random.randint(0, geo.width() - self.width()), random.randint(0, geo.height() - self.height()))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, "_settings_callback"):
            self._settings_callback()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background:#050A05; color:#00FF9D; border:1px solid #00FF9D44; font-family:'Rajdhani'; }")
        s = menu.addAction("Settings"); r = menu.addAction("Restart"); e = menu.addAction("Exit")
        action = menu.exec(event.globalPos())
        if action == s: self.mouseDoubleClickEvent(None)
        elif action == r: self._restart_app()
        elif action == e: QApplication.quit()

    def _restart_app(self):
        import sys, subprocess
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit()

    def show_hud(self):
        self.show(); self.fade_anim.stop(); self.fade_anim.setStartValue(self.windowOpacity()); self.fade_anim.setEndValue(1.0); self.fade_anim.start()

    def hide_hud(self):
        self.fade_anim.stop(); self.fade_anim.setStartValue(self.windowOpacity()); self.fade_anim.setEndValue(0.0); self.fade_anim.start()

    def set_status(self, status: str):
        self.status = status
        intervals = {"THINKING": (16, 6), "LISTENING": (16, 1.5), "SPEAKING": (16, 2), "IDLE": (50, 0.4)}
        iv, step = intervals.get(status, (50, 0.4))
        self.timer.setInterval(iv); self.angle_step = step

    def set_command(self, cmd: str):
        self.last_command = cmd
        QTimer.singleShot(8000, lambda: setattr(self, 'last_command', ""))

    def set_response(self, text: str): self.ai_response = text

    def update_stats(self, cpu: float, ram: float):
        self.cpu_usage = cpu; self.ram_usage = ram

    def set_emotion(self, emotion: str):
        if emotion in _EMOTION_PALETTE: self.current_emotion = emotion; self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height(); cx, cy = w/2, h/2; center = QPointF(cx, cy); radius = min(w, h)/2 - 4
        self.angle += self.angle_step; self.pulse_timer += 0.04
        color = _EMOTION_PALETTE.get(self.current_emotion, _GREEN)

        # 0. Grid
        if not self._grid_pixmap:
            pm = QPixmap(w, h); pm.fill(Qt.GlobalColor.transparent); gp = QPainter(pm)
            gp.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 18), 1))
            for x in range(0, w+28, 28): gp.drawLine(x, 0, x, h)
            for y in range(0, h+28, 28): gp.drawLine(0, y, w, y)
            gp.end(); self._grid_pixmap = pm
        p.drawPixmap(0, 0, self._grid_pixmap)

        # 1. Halo
        g = QRadialGradient(center, radius)
        g.setColorAt(0.55, QColor(0,0,0,0)); g.setColorAt(0.8, QColor(color.red(), color.green(), color.blue(), 18)); g.setColorAt(1, QColor(0,0,0,0))
        p.setBrush(g); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QRectF(cx-radius, cy-radius, radius*2, radius*2))

        # 2. State Core
        if self.status == "LISTENING":
            for i in range(len(self.ripple_phases)):
                self.ripple_phases[i] = (self.ripple_phases[i] + 0.025) % 1.0
                r = radius * 0.75 * self.ripple_phases[i]
                p.setBrush(QColor(color.red(), color.green(), color.blue(), int(200*(1-self.ripple_phases[i])**2)))
                p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
        elif self.status == "THINKING":
            grad = QConicalGradient(center, -self.angle % 360)
            grad.setColorAt(0, color); grad.setColorAt(0.3, QColor(0,0,0,0))
            p.setBrush(grad); p.drawEllipse(QRectF(cx-radius*0.58, cy-radius*0.58, radius*1.16, radius*1.16))
            p.setBrush(QColor(0,0,0,200)); p.drawEllipse(QRectF(cx-radius*0.3, cy-radius*0.3, radius*0.6, radius*0.6))
        elif self.status == "SPEAKING":
            for i in range(len(self.eq_bars)):
                self.eq_bars[i] += (random.uniform(0.15, 0.95) - self.eq_bars[i]) * 0.25
                bh = radius * 0.65 * self.eq_bars[i]; bx = cx - (7*radius*0.17)/2 + i*radius*0.17
                g = QLinearGradient(bx, cy-bh/2, bx, cy+bh/2); g.setColorAt(0, Qt.GlobalColor.white); g.setColorAt(1, color)
                p.setBrush(g); p.drawRoundedRect(QRectF(bx, cy-bh/2, radius*0.12, bh), radius*0.06, radius*0.06)
        else:
            pulse = (math.sin(self.pulse_timer*1.2)+1)/2; core = radius*(0.32+pulse*0.05)
            g = QRadialGradient(center, core); g.setColorAt(0, Qt.GlobalColor.white); g.setColorAt(0.35, color); g.setColorAt(1, QColor(0,0,0,0))
            p.setBrush(g); p.drawEllipse(QRectF(cx-core, cy-core, core*2, core*2))

        # 3. Ring
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 55), 1, Qt.PenStyle.DotLine))
        rr = radius * 0.96; p.drawEllipse(QRectF(cx-rr, cy-rr, rr*2, rr*2))
        p.setPen(QPen(color, 2)); p.drawArc(QRectF(cx-rr, cy-rr, rr*2, rr*2), int(self.angle*16)%5760, 880)

        # 4. UI
        labels = {"IDLE":"READY", "LISTENING":"● LISTENING", "THINKING":"◌ PROCESSING", "SPEAKING":"▶ SPEAKING"}
        txt = labels.get(self.status, self.status); p.setFont(QFont("Orbitron", 8, QFont.Weight.Bold))
        tw = p.fontMetrics().horizontalAdvance(txt)+20; tr = QRectF(cx-tw/2, cy+radius*0.72, tw, 22)
        p.setBrush(QColor(0,0,0,160)); p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 100), 1))
        p.drawRoundedRect(tr, 11, 11); p.setPen(color); p.drawText(tr, Qt.AlignmentFlag.AlignCenter, txt)
        p.setFont(QFont("Rajdhani", 8)); p.setPen(QColor(200,200,200,140))
        p.drawText(QRectF(cx-radius+6, cy-18, 54, 36), Qt.AlignmentFlag.AlignLeft, f"CPU\n{int(self.cpu_usage)}%")
        p.drawText(QRectF(cx+radius-60, cy-18, 54, 36), Qt.AlignmentFlag.AlignRight, f"RAM\n{int(self.ram_usage)}%")
        if self.last_command:
            p.setFont(QFont("Rajdhani", 9, QFont.Weight.DemiBold)); p.setPen(Qt.GlobalColor.white)
            cmd = p.fontMetrics().elidedText(f'"{self.last_command}"', Qt.TextElideMode.ElideRight, int(radius*1.7))
            p.drawText(QPointF(cx-p.fontMetrics().horizontalAdvance(cmd)/2, cy-radius*0.8), cmd)
        if self.ai_response:
            p.setFont(QFont("Rajdhani", 9)); p.setPen(color)
            res = p.fontMetrics().elidedText(self.ai_response, Qt.TextElideMode.ElideRight, int(radius*1.8))
            p.drawText(QPointF(cx-p.fontMetrics().horizontalAdvance(res)/2, cy-radius*0.65), res)

if __name__ == "__main__":
    import sys; from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv); w = HUDWindow(type("C", (), {"get": lambda s,k,d=340: d})()); w.show(); sys.exit(app.exec())
