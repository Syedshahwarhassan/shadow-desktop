from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSlider, QFormLayout, QGroupBox, QCheckBox, 
    QTabWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QIcon
from config_manager import config_manager
import os
import sys

class SettingsWindow(QWidget):
    def __init__(self, hud):
        super().__init__()
        self.hud = hud
        self.setWindowTitle("Shadow System Settings")
        self.setFixedSize(500, 650)
        
        # Dark premium theme
        self.setStyleSheet("""
            QWidget {
                background-color: #0A141E;
                color: #00D4FF;
                font-family: 'Rajdhani', sans-serif;
                font-size: 14px;
            }
            QTabWidget::pane {
                border: 1px solid #1A2832;
                background: #0A141E;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #050A0F;
                border: 1px solid #1A2832;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 10px 20px;
                margin-right: 2px;
                color: #0088AA;
                font-family: 'Orbitron';
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #0A141E;
                color: #00D4FF;
                border-bottom: 2px solid #00D4FF;
            }
            QGroupBox {
                border: 1px solid #1A2832;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 15px;
                font-weight: bold;
                text-transform: uppercase;
                color: #00D4FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #0A141E;
            }
            QLineEdit {
                background-color: #050A0F;
                border: 1px solid #1A2832;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #00D4FF;
            }
            QLineEdit[readOnly="true"] {
                color: #555;
                background-color: #020508;
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
            QSlider::groove:horizontal {
                border: 1px solid #1A2832;
                height: 4px;
                background: #050A0F;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #00D4FF;
                width: 18px;
                height: 18px;
                margin: -7px 0;
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
        header = QLabel("SHADOW SYSTEM CONTROL")
        header.setStyleSheet("font-family: 'Orbitron'; font-size: 20px; color: #00D4FF; margin: 15px 0;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        
        # ── General Tab ───────────────────────────────────────────────────────
        general_tab = QWidget()
        gen_layout = QVBoxLayout(general_tab)
        
        core_box = QGroupBox("Core Configuration")
        core_form = QFormLayout()
        self.wake_input = QLineEdit(config_manager.get("wake_word", "shadow"))
        core_form.addRow("Wake Word:", self.wake_input)
        self.hotkey_input = QLineEdit(config_manager.get("hotkey", "win+shift+s"))
        core_form.addRow("Toggle Hotkey:", self.hotkey_input)
        self.exit_hotkey_input = QLineEdit(config_manager.get("exit_hotkey", "ctrl+shift+q"))
        core_form.addRow("Exit Hotkey:", self.exit_hotkey_input)
        self.autostart_cb = QCheckBox("Start with Windows")
        self.autostart_cb.setChecked(config_manager.get("autostart", False))
        core_form.addRow("", self.autostart_cb)
        core_box.setLayout(core_form)
        gen_layout.addWidget(core_box)

        vis_box = QGroupBox("Visual Parameters")
        vis_form = QFormLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(config_manager.get("hud.opacity", 0.8) * 100))
        vis_form.addRow("HUD Opacity:", self.opacity_slider)
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(100, 500)
        self.size_slider.setValue(config_manager.get("hud.diameter", 300))
        vis_form.addRow("HUD Size:", self.size_slider)
        vis_box.setLayout(vis_form)
        gen_layout.addWidget(vis_box)

        api_box = QGroupBox("Neural Network Keys")
        api_form = QFormLayout()
        self.openrouter_key = QLineEdit(config_manager.get("api_keys.openrouter", ""))
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("OpenRouter:", self.openrouter_key)
        self.openai_key = QLineEdit(config_manager.get("api_keys.openai", ""))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("OpenAI Key:", self.openai_key)
        self.weather_key = QLineEdit(config_manager.get("api_keys.openweathermap", ""))
        api_form.addRow("Weather API:", self.weather_key)
        api_box.setLayout(api_form)
        gen_layout.addWidget(api_box)
        gen_layout.addStretch()
        
        self.tabs.addTab(general_tab, "GENERAL")

        # ── Sync Tab ──────────────────────────────────────────────────────────
        sync_tab = QWidget()
        sync_layout = QVBoxLayout(sync_tab)
        
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #050A0F; border-radius: 8px; padding: 10px;")
        status_layout = QHBoxLayout(status_frame)
        status_layout.addWidget(QLabel("SYNC STATUS:"))
        
        self.status_dot = QFrame()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("background-color: #FF4444; border-radius: 6px;") # Default red
        status_layout.addWidget(self.status_dot)
        
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet("font-weight: bold; font-family: 'Orbitron'; font-size: 10px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        sync_layout.addWidget(status_frame)

        sync_box = QGroupBox("Relay Configuration")
        sync_form = QFormLayout()
        
        self.sync_enabled_cb = QCheckBox("Enable Multi-Device Sync")
        self.sync_enabled_cb.setChecked(config_manager.get("sync_enabled", False))
        sync_form.addRow("", self.sync_enabled_cb)
        
        self.sync_url = QLineEdit(config_manager.get("sync_server_url", "ws://localhost:8765"))
        sync_form.addRow("Relay URL:", self.sync_url)
        
        self.sync_room = QLineEdit(config_manager.get("sync_room_id", "shadow-default"))
        sync_form.addRow("Room ID:", self.sync_room)
        
        self.device_name = QLineEdit(config_manager.get("device_name", "My PC"))
        sync_form.addRow("Device Name:", self.device_name)
        
        sync_box.setLayout(sync_form)
        sync_layout.addWidget(sync_box)

        id_box = QGroupBox("Identity")
        id_layout = QVBoxLayout()
        
        id_row = QHBoxLayout()
        self.device_id_field = QLineEdit(config_manager.get("device_id", ""))
        self.device_id_field.setReadOnly(True)
        id_row.addWidget(self.device_id_field)
        
        copy_btn = QPushButton("COPY")
        copy_btn.setFixedWidth(60)
        copy_btn.setStyleSheet("font-size: 10px; padding: 5px;")
        copy_btn.clicked.connect(self.copy_id)
        id_row.addWidget(copy_btn)
        id_layout.addLayout(id_row)
        
        id_box.setLayout(id_layout)
        sync_layout.addWidget(id_box)
        sync_layout.addStretch()
        
        self.tabs.addTab(sync_tab, "SYNC")
        
        main_layout.addWidget(self.tabs)

        # ── Footer Buttons ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("SAVE & APPLY")
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("DISCARD")
        cancel_btn.setStyleSheet("background-color: #1A2832; color: #00D4FF; border: 1px solid #00D4FF;")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def copy_id(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.device_id_field.text())

    def update_sync_status(self, status: int):
        """0=Red, 1=Amber, 2=Green"""
        colors = ["#FF4444", "#FFBB00", "#00FF88"]
        texts = ["DISCONNECTED", "RECONNECTING", "CONNECTED"]
        if 0 <= status < len(colors):
            self.status_dot.setStyleSheet(f"background-color: {colors[status]}; border-radius: 6px;")
            self.status_label.setText(texts[status])
            self.status_label.setStyleSheet(f"color: {colors[status]}; font-weight: bold; font-family: 'Orbitron'; font-size: 10px;")

    def save(self):
        # Update config
        config_manager.set("wake_word", self.wake_input.text().lower())
        config_manager.set("hotkey", self.hotkey_input.text().lower())
        config_manager.set("exit_hotkey", self.exit_hotkey_input.text().lower())
        config_manager.set("autostart", self.autostart_cb.isChecked())
        config_manager.set("hud.opacity", self.opacity_slider.value() / 100.0)
        config_manager.set("hud.diameter", self.size_slider.value())
        config_manager.set("api_keys.openrouter", self.openrouter_key.text())
        config_manager.set("api_keys.openai", self.openai_key.text())
        config_manager.set("api_keys.openweathermap", self.weather_key.text())
        
        # Sync settings
        config_manager.set("sync_enabled", self.sync_enabled_cb.isChecked())
        config_manager.set("sync_server_url", self.sync_url.text())
        config_manager.set("sync_room_id", self.sync_room.text())
        config_manager.set("device_name", self.device_name.text())
        
        # Apply visual changes immediately
        self.hud.setWindowOpacity(config_manager.get("hud.opacity"))
        
        # Handle Autostart (Windows Registry)
        self._handle_autostart(self.autostart_cb.isChecked())
        
        # Notify user to restart for sync changes if needed (simplified: just save)
        print("[SETTINGS] Saved. Some changes (like Sync toggle) may require restart.")
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
