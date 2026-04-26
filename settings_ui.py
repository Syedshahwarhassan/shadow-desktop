from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QFormLayout, QGroupBox, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from config_manager import config_manager
import os
import sys

class SettingsWindow(QWidget):
    def __init__(self, hud):
        super().__init__()
        self.hud = hud
        self.setWindowTitle("Shadow System Settings")
        self.setFixedSize(450, 600)
        
        # Dark premium theme
        self.setStyleSheet("""
            QWidget {
                background-color: #0A141E;
                color: #00D4FF;
                font-family: 'Rajdhani', sans-serif;
                font-size: 14px;
            }
            QGroupBox {
                border: 1px solid #00D4FF;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #050A0F;
                border: 1px solid #1A2832;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #00D4FF;
            }
            QPushButton {
                background-color: #00D4FF;
                color: #0A141E;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-family: 'Orbitron';
            }
            QPushButton:hover {
                background-color: #00A3C2;
            }
            QSlider::handle:horizontal {
                background: #00D4FF;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QCheckBox {
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #00D4FF;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #00D4FF;
            }
        """)

        main_layout = QVBoxLayout()
        
        # Header
        header = QLabel("SHADOW INTERFACE CONFIG")
        header.setStyleSheet("font-family: 'Orbitron'; font-size: 18px; color: #00D4FF; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # ── General Settings ──────────────────────────────────────────────────
        gen_box = QGroupBox("Core Configuration")
        gen_layout = QFormLayout()
        
        self.wake_input = QLineEdit(config_manager.get("wake_word", "shadow"))
        gen_layout.addRow("Wake Word:", self.wake_input)
        
        self.hotkey_input = QLineEdit(config_manager.get("hotkey", "win+shift+s"))
        gen_layout.addRow("Toggle Hotkey:", self.hotkey_input)
        
        self.autostart_cb = QCheckBox("Start with Windows")
        self.autostart_cb.setChecked(config_manager.get("autostart", False))
        gen_layout.addRow("", self.autostart_cb)
        
        gen_box.setLayout(gen_layout)
        main_layout.addWidget(gen_box)

        # ── Visual Settings ───────────────────────────────────────────────────
        vis_box = QGroupBox("Visual Parameters")
        vis_layout = QFormLayout()
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(config_manager.get("hud.opacity", 0.8) * 100))
        vis_layout.addRow("HUD Opacity:", self.opacity_slider)
        
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(100, 500)
        self.size_slider.setValue(config_manager.get("hud.diameter", 300))
        vis_layout.addRow("HUD Size:", self.size_slider)
        
        vis_box.setLayout(vis_layout)
        main_layout.addWidget(vis_box)

        # ── API Credentials ──────────────────────────────────────────────────
        api_box = QGroupBox("Neural Network Keys")
        api_layout = QFormLayout()
        
        self.openrouter_key = QLineEdit(config_manager.get("api_keys.openrouter", ""))
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("OpenRouter:", self.openrouter_key)
        
        self.openai_key = QLineEdit(config_manager.get("api_keys.openai", ""))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("OpenAI Key:", self.openai_key)
        
        self.weather_key = QLineEdit(config_manager.get("api_keys.openweathermap", ""))
        api_layout.addRow("Weather API:", self.weather_key)
        
        api_box.setLayout(api_layout)
        main_layout.addWidget(api_box)

        # ── Footer Buttons ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("SAVE & SYNC")
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("DISCARD")
        cancel_btn.setStyleSheet("background-color: #1A2832; color: #00D4FF; border: 1px solid #00D4FF;")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def save(self):
        # Update config
        config_manager.set("wake_word", self.wake_input.text().lower())
        config_manager.set("hotkey", self.hotkey_input.text().lower())
        config_manager.set("autostart", self.autostart_cb.isChecked())
        config_manager.set("hud.opacity", self.opacity_slider.value() / 100.0)
        config_manager.set("hud.diameter", self.size_slider.value())
        config_manager.set("api_keys.openrouter", self.openrouter_key.text())
        config_manager.set("api_keys.openai", self.openai_key.text())
        config_manager.set("api_keys.openweathermap", self.weather_key.text())
        
        # Apply visual changes immediately
        self.hud.setWindowOpacity(config_manager.get("hud.opacity"))
        # self.hud.resize(self.size_slider.value(), self.size_slider.value())
        
        # Handle Autostart (Windows Registry)
        self._handle_autostart(self.autostart_cb.isChecked())
        
        self.close()

    def _handle_autostart(self, enabled):
        if sys.platform != "win32":
            return
        
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "ShadowAssistant"
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                # Use sys.executable if running as script, or sys.argv[0] if frozen
                if getattr(sys, 'frozen', False):
                    cmd = f'"{sys.executable}"'
                else:
                    cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[SETTINGS] Autostart error: {e}")
