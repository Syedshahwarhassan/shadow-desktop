from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont
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
        
        self.diameter = config.get("hud.diameter", 150)
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
        self.emotion_colors = {
            "HAPPY":   QColor(0, 255, 128),  # Spring Green
            "EXCITED": QColor(255, 215, 0),  # Gold
            "SAD":     QColor(100, 100, 255), # Soft Blue
            "ANGRY":   QColor(255, 69, 0),   # Red-Orange
            "CURIOUS": QColor(255, 0, 255),  # Magenta
            "CALM":    QColor(0, 212, 255),  # Default Cyan
        }
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16) # ~60 FPS
        
        self.pulse_timer = 0

    def _corner_window(self):
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 40
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

    def set_status(self, status):
        self.status = status

    def set_command(self, cmd):
        self.last_command = cmd
        QTimer.singleShot(5000, lambda: self.clear_command())

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
            # Trigger a refresh
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        scale_factor = self.diameter / 400.0
        painter.scale(scale_factor, scale_factor)
        
        fixed_diameter = 400
        center = QPointF(fixed_diameter / 2, fixed_diameter / 2)
        
        self.angle += 1 if self.status == "IDLE" else 5
        self.pulse_timer += 0.05
        pulse_val = (math.sin(self.pulse_timer) + 1) / 2 # 0 to 1
        
        theme_color = QColor(self.config.get("hud.theme_color", "#00D4FF"))
        
        # Draw Background Glow
        gradient = QRadialGradient(center, fixed_diameter / 2)
        gradient.setColorAt(0, QColor(5, 10, 15, 150))
        gradient.setColorAt(0.8, QColor(0, 0, 0, 50))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, fixed_diameter/2, fixed_diameter/2)
        
        # Rotating Arcs
        pen = QPen(theme_color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Outer Ring
        rect = QRectF(10, 10, fixed_diameter - 20, fixed_diameter - 20)
        painter.drawArc(rect, int(self.angle * 16), 120 * 16)
        painter.drawArc(rect, int((self.angle + 180) * 16), 120 * 16)
        
        # Inner Ring
        pen.setWidth(1)
        pen.setColor(QColor(0, 102, 255))
        painter.setPen(pen)
        rect_inner = QRectF(40, 40, fixed_diameter - 80, fixed_diameter - 80)
        painter.drawArc(rect_inner, int(-self.angle * 2 * 16), 90 * 16)
        painter.drawArc(rect_inner, int((-self.angle * 2 + 180) * 16), 90 * 16)
        
        # Center Orb
        base_color = self.emotion_colors.get(self.current_emotion, theme_color)
        
        if self.status == "LISTENING":
            orb_color = QColor(base_color.red(), base_color.green(), base_color.blue(), int(150 + pulse_val * 105))
        elif self.status == "THINKING":
            orb_color = QColor(255, 170, 0, int(180 + pulse_val * 75)) # Keep Thinking as Orange
        elif self.status == "SPEAKING":
            orb_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 220)
        else:
            orb_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 100)
            
        painter.setBrush(orb_color)
        painter.setPen(Qt.PenStyle.NoPen)
        orb_size = 40 + (pulse_val * 10 if self.status in ["LISTENING", "THINKING"] else 0)
        painter.drawEllipse(center, orb_size, orb_size)
        
        # Text Info
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Orbitron", 10))
        
        # Time (Top)
        current_time = time.strftime("%H:%M:%S")
        painter.drawText(int(center.x() - 40), 30, current_time)
        
        # Command (Left)
        if self.last_command:
            painter.setFont(QFont("Rajdhani", 9))
            painter.drawText(20, int(center.y()), f"> {self.last_command}")
            
        # Stats (Right)
        painter.setFont(QFont("Rajdhani", 8))
        stats_text = f"CPU: {self.cpu_usage}%\nRAM: {self.ram_usage}%"
        painter.drawText(fixed_diameter - 80, int(center.y() - 10), stats_text)
        
        # Response (Bottom)
        if self.ai_response:
            painter.setFont(QFont("Rajdhani", 10))
            metrics = painter.fontMetrics()
            wrapped_text = metrics.elidedText(self.ai_response, Qt.TextElideMode.ElideRight, fixed_diameter - 40)
            painter.drawText(20, fixed_diameter - 40, wrapped_text)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = HUDWindow({"hud.diameter": 400, "hud.theme_color": "#00D4FF"})
    window.show()
    sys.exit(app.exec())
