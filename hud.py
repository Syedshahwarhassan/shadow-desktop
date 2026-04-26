from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont, QConicalGradient
import math
import time

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
        
        self.angle = 0
        self.pulse = 0
        self.status = "IDLE" # IDLE, LISTENING, THINKING, SPEAKING
        self.last_command = ""
        self.ai_response = ""
        self.cpu_usage = 0
        self.ram_usage = 0
        self.current_emotion = "CALM"
        
        # Enhanced Color Palette
        self.emotion_colors = {
            "HAPPY":   QColor(0, 255, 150, 200),  # Emerald
            "EXCITED": QColor(255, 200, 0, 200),    # Vivid Gold
            "SAD":     QColor(0, 150, 255, 200),    # Ocean Blue
            "ANGRY":   QColor(255, 50, 50, 200),    # Crimson
            "CURIOUS": QColor(200, 0, 255, 200),    # Neon Purple
            "CALM":    QColor(0, 212, 255, 200),    # Electric Cyan
        }
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16) # ~60 FPS
        
        self.pulse_timer = 0
        self.noise_offset = 0

    def _corner_window(self):
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 60
        self.move(x, y)

    def enterEvent(self, event):
        # Dodge the mouse by jumping to a random position
        import random
        screen = self.screen().availableGeometry()
        max_x = screen.width() - self.width()
        max_y = screen.height() - self.height()
        
        new_x = random.randint(0, max_x)
        new_y = random.randint(0, max_y)
        self.move(new_x, new_y)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_settings()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0A141E;
                color: #00D4FF;
                border: 1px solid #00D4FF;
                font-family: 'Rajdhani';
            }
            QMenu::item:selected {
                background-color: #00D4FF;
                color: #0A141E;
            }
        """)
        settings_action = menu.addAction("Settings")
        exit_action = menu.addAction("Exit System")
        
        action = menu.exec(event.globalPos())
        if action == settings_action:
            self.open_settings()
        elif action == exit_action:
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()

    def open_settings(self):
        # This will be overridden or called by main.py
        if hasattr(self, '_settings_callback'):
            self._settings_callback()
        else:
            print("[HUD] Settings callback not connected")

    def set_status(self, status):
        self.status = status
        # Reset timers/angles for snappy transition
        if status == "THINKING":
            self.angle_step = 8
        elif status == "LISTENING":
            self.angle_step = 2
        else:
            self.angle_step = 1

    def set_command(self, cmd):
        self.last_command = cmd
        QTimer.singleShot(8000, lambda: self.clear_command())

    def clear_command(self):
        self.last_command = ""

    def set_response(self, text):
        self.ai_response = text

    def update_stats(self, cpu, ram):
        self.cpu_usage = cpu
        self.ram_usage = ram

    def set_emotion(self, emotion):
        if emotion in self.emotion_colors:
            self.current_emotion = emotion
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        rect = self.rect()
        center = QPointF(rect.width() / 2, rect.height() / 2)
        radius = min(rect.width(), rect.height()) / 2
        
        self.angle += getattr(self, 'angle_step', 1)
        self.pulse_timer += 0.05
        pulse_val = (math.sin(self.pulse_timer) + 1) / 2 # 0 to 1
        
        theme_color = self.emotion_colors.get(self.current_emotion, QColor(0, 212, 255))
        
        # 1. Background Glow
        glow_grad = QRadialGradient(center, radius)
        glow_grad.setColorAt(0, QColor(theme_color.red(), theme_color.green(), theme_color.blue(), 40))
        glow_grad.setColorAt(0.7, QColor(0, 0, 0, 0))
        painter.setBrush(glow_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        
        # 2. Outer Technical Rings
        self._draw_rings(painter, center, radius, theme_color, pulse_val)
        
        # 3. State-Specific Visuals (The "Neural Core")
        if self.status == "LISTENING":
            self._draw_listening_waves(painter, center, radius, theme_color, pulse_val)
        elif self.status == "THINKING":
            self._draw_thinking_ring(painter, center, radius, theme_color)
        elif self.status == "SPEAKING":
            self._draw_speaking_core(painter, center, radius, theme_color, pulse_val)
        else: # IDLE
            self._draw_idle_core(painter, center, radius, theme_color, pulse_val)
            
        # 4. Text & Metadata
        self._draw_ui_elements(painter, rect, center, radius, theme_color)

    def _draw_rings(self, painter, center, radius, color, pulse):
        pen = QPen(color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        # Outer dotted ring
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius * 0.85, radius * 0.85)
        
        # Rotating segments
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidth(3)
        painter.setPen(pen)
        
        # Ring 1 (Clockwise)
        rect_1 = QRectF(center.x() - radius*0.8, center.y() - radius*0.8, radius*1.6, radius*1.6)
        painter.drawArc(rect_1, int(self.angle * 16), 60 * 16)
        painter.drawArc(rect_1, int((self.angle + 180) * 16), 60 * 16)
        
        # Ring 2 (Counter-clockwise)
        pen.setWidth(1)
        painter.setPen(pen)
        rect_2 = QRectF(center.x() - radius*0.75, center.y() - radius*0.75, radius*1.5, radius*1.5)
        painter.drawArc(rect_2, int(-self.angle * 1.5 * 16), 120 * 16)

    def _draw_listening_waves(self, painter, center, radius, color, pulse):
        # Simulated audio waveform
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        for i in range(8):
            wave_radius = radius * 0.3 + (i * 10) + (pulse * 5)
            alpha = int(255 * (1 - i/8.0))
            pen.setColor(QColor(color.red(), color.green(), color.blue(), alpha))
            painter.setPen(pen)
            
            # Draw jittery circles
            jitter = math.sin(self.pulse_timer * 5 + i) * 5
            painter.drawEllipse(center, wave_radius + jitter, wave_radius - jitter)

    def _draw_thinking_ring(self, painter, center, radius, color):
        # Scanning radar effect
        grad = QConicalGradient(center, self.angle % 360)
        grad.setColorAt(0, color)
        grad.setColorAt(0.2, QColor(0, 0, 0, 0))
        
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius * 0.6, radius * 0.6)
        
        # Inner spinning hex or cross
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle * 4)
        for i in range(4):
            painter.rotate(90)
            painter.drawLine(0, -20, 0, -40)
        painter.restore()

    def _draw_speaking_core(self, painter, center, radius, color, pulse):
        # Energetic pulsing core
        core_size = radius * 0.4 + (pulse * 15)
        grad = QRadialGradient(center, core_size)
        grad.setColorAt(0, color)
        grad.setColorAt(0.8, QColor(color.red(), color.green(), color.blue(), 100))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, core_size, core_size)
        
        # Particle effect simulation (dots)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        for i in range(5):
            angle = (self.pulse_timer * 10 + i * 72) * (math.pi / 180)
            px = center.x() + math.cos(angle) * (core_size + 10)
            py = center.y() + math.sin(angle) * (core_size + 10)
            painter.drawPoint(QPointF(px, py))

    def _draw_idle_core(self, painter, center, radius, color, pulse):
        core_size = radius * 0.35
        alpha = int(100 + pulse * 50)
        grad = QRadialGradient(center, core_size)
        grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), alpha))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, core_size, core_size)

    def _draw_ui_elements(self, painter, rect, center, radius, color):
        # 1. Status Label (Top)
        painter.setPen(color)
        painter.setFont(QFont("Orbitron", 10, QFont.Weight.Bold))
        status_text = self.status
        if self.status == "IDLE": status_text = "SYSTEM READY"
        elif self.status == "LISTENING": status_text = "LISTENING..."
        elif self.status == "THINKING": status_text = "PROCESSING..."
        elif self.status == "SPEAKING": status_text = "SHADOW SPEAKING"
        
        metrics = painter.fontMetrics()
        tx = int(center.x() - metrics.horizontalAdvance(status_text) / 2)
        painter.drawText(tx, int(center.y() - radius + 30), status_text)
        
        # 2. System Stats (Sides)
        painter.setFont(QFont("Rajdhani", 8))
        painter.setPen(QColor(200, 200, 200, 180))
        
        # Left: CPU
        cpu_rect = QRectF(center.x() - radius + 10, center.y() - 15, 60, 30)
        painter.drawText(cpu_rect, Qt.AlignmentFlag.AlignLeft, f"CPU\n{int(self.cpu_usage)}%")
        
        # Right: RAM
        ram_rect = QRectF(center.x() + radius - 70, center.y() - 15, 60, 30)
        painter.drawText(ram_rect, Qt.AlignmentFlag.AlignRight, f"RAM\n{int(self.ram_usage)}%")
        
        # 3. User Command (Bottom center, small)
        if self.last_command:
            painter.setFont(QFont("Rajdhani", 9, QFont.Weight.DemiBold))
            painter.setPen(QColor(255, 255, 255, 200))
            cmd_text = f"\"{self.last_command}\""
            wrapped_cmd = metrics.elidedText(cmd_text, Qt.TextElideMode.ElideRight, int(radius * 1.5))
            cx = int(center.x() - metrics.horizontalAdvance(wrapped_cmd) / 2)
            painter.drawText(cx, int(center.y() + radius - 45), wrapped_cmd)

        # 4. AI Response (Bottom)
        if self.ai_response:
            painter.setFont(QFont("Rajdhani", 10))
            painter.setPen(Qt.GlobalColor.white)
            res_metrics = painter.fontMetrics()
            # Wrap text manually for the HUD area
            wrapped_res = res_metrics.elidedText(self.ai_response, Qt.TextElideMode.ElideRight, int(radius * 1.8))
            rx = int(center.x() - res_metrics.horizontalAdvance(wrapped_res) / 2)
            painter.drawText(rx, int(center.y() + radius - 20), wrapped_res)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = HUDWindow({"hud.diameter": 400, "hud.theme_color": "#00D4FF"})
    window.show()
    sys.exit(app.exec())
