from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QFormLayout
from PyQt6.QtCore import Qt
from config_manager import config_manager

class SettingsWindow(QWidget):
    def __init__(self, hud):
        super().__init__()
        self.hud = hud
        self.setWindowTitle("AntiGravity Settings")
        self.setFixedSize(400, 500)
        self.setStyleSheet("background-color: #050A0F; color: #00D4FF; font-family: Orbitron;")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        # Wake Word
        self.wake_input = QLineEdit(config_manager.get("wake_word"))
        form.addRow("Wake Word:", self.wake_input)
        
        # Opacity
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(int(config_manager.get("hud.opacity") * 100))
        form.addRow("HUD Opacity:", self.opacity_slider)
        
        # API Keys
        self.openai_key = QLineEdit(config_manager.get("api_keys.openai"))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("OpenAI Key:", self.openai_key)
        
        self.weather_key = QLineEdit(config_manager.get("api_keys.openweathermap"))
        form.addRow("Weather Key:", self.weather_key)
        
        layout.addLayout(form)
        
        # Save Button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)

    def save(self):
        config_manager.set("wake_word", self.wake_input.text())
        config_manager.set("hud.opacity", self.opacity_slider.value() / 100.0)
        config_manager.set("api_keys.openai", self.openai_key.text())
        config_manager.set("api_keys.openweathermap", self.weather_key.text())
        
        self.hud.setWindowOpacity(config_manager.get("hud.opacity"))
        self.close()
