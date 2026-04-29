from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSlider, QStackedWidget, QFrame, QGraphicsDropShadowEffect,
    QCheckBox, QFormLayout
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtProperty, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPalette
from config_manager import config_manager
import os
import sys

class ModernSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal):
        super().__init__(orientation)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #1A2634;
                height: 6px;
                background: #0D1621;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00FF9D;
                border: 2px solid #00FF9D;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #FFFFFF;
                border-color: #00FF9D;
            }
        """)

class NavButton(QPushButton):
    def __init__(self, text, icon_path=None):
        super().__init__(text)
        self.setCheckable(True)
        self.setMinimumHeight(45)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #A0AAB4;
                border: none;
                text-align: left;
                padding-left: 20px;
                font-family: 'Rajdhani';
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #00FF9D;
                background: rgba(0, 255, 157, 0.05);
            }
            QPushButton:checked {
                color: #00FF9D;
                background: rgba(0, 255, 157, 0.1);
                border-left: 3px solid #00FF9D;
            }
        """)

class SettingsWindow(QWidget):
    def __init__(self, hud):
        super().__init__()
        self.hud = hud
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(700, 550)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            #MainContainer {
                background-color: rgba(10, 20, 30, 0.95);
                border: 1px solid #00FF9D;
                border-radius: 15px;
            }
        """)
        self.layout.addWidget(self.container)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.setup_title_bar()
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.container_layout.addLayout(self.content_layout)
        
        self.setup_sidebar()
        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background: transparent; padding: 20px;")
        self.content_layout.addWidget(self.pages)
        self.setup_pages()
        self.nav_ai.setChecked(True)
        self.pages.setCurrentIndex(0)

    def setup_title_bar(self):
        title_bar = QFrame()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("background: rgba(0, 0, 0, 0.2); border-top-left-radius: 15px; border-top-right-radius: 15px;")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(20, 0, 10, 0)
        title = QLabel("SHADOW SETTINGS")
        title.setStyleSheet("color: #00FF9D; font-family: 'Orbitron'; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        tb_layout.addWidget(title)
        tb_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #A0AAB4; font-size: 18px; border-radius: 5px; } QPushButton:hover { background: #FF4B4B; color: white; }")
        tb_layout.addWidget(close_btn)
        self.container_layout.addWidget(title_bar)
        self._old_pos = None
        title_bar.mousePressEvent = self.title_press
        title_bar.mouseMoveEvent = self.title_move

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background: rgba(0, 0, 0, 0.3); border-bottom-left-radius: 15px;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 20, 0, 0)
        side_layout.setSpacing(5)
        self.nav_ai = NavButton("AI & BRAIN")
        self.nav_hud = NavButton("HUD APPEARANCE")
        self.nav_system = NavButton("SYSTEM")
        from PyQt6.QtWidgets import QButtonGroup
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.nav_ai, 0)
        self.btn_group.addButton(self.nav_hud, 1)
        self.btn_group.addButton(self.nav_system, 2)
        self.btn_group.buttonClicked.connect(lambda b: self.pages.setCurrentIndex(self.btn_group.id(b)))
        side_layout.addWidget(self.nav_ai)
        side_layout.addWidget(self.nav_hud)
        side_layout.addWidget(self.nav_system)
        side_layout.addStretch()
        self.save_btn = QPushButton("SAVE CHANGES")
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setStyleSheet("QPushButton { background: #00FF9D; color: #050A0F; border: none; font-family: 'Orbitron'; font-weight: bold; font-size: 12px; border-bottom-left-radius: 15px; } QPushButton:hover { background: #FFFFFF; }")
        side_layout.addWidget(self.save_btn)
        self.content_layout.addWidget(sidebar)

    def setup_pages(self):
        ai_page = QWidget(); ai_layout = QVBoxLayout(ai_page); ai_layout.setSpacing(15)
        ai_layout.addWidget(self.create_header("AI CONFIGURATION"))
        self.openrouter_input = self.create_input("OpenRouter API Key", config_manager.get("api_keys.openrouter"), password=True)
        self.openai_input = self.create_input("OpenAI API Key", config_manager.get("api_keys.openai"), password=True)
        self.wake_input = self.create_input("Wake Word", config_manager.get("wake_word"))
        ai_layout.addWidget(self.openrouter_input); ai_layout.addWidget(self.openai_input); ai_layout.addWidget(self.wake_input); ai_layout.addStretch(); self.pages.addWidget(ai_page)

        hud_page = QWidget(); hud_layout = QVBoxLayout(hud_page)
        hud_layout.addWidget(self.create_header("VISUAL INTERFACE"))
        
        self.hud_startup_cb = QCheckBox("Show HUD on startup")
        self.hud_startup_cb.setChecked(config_manager.get("hud_visible_on_start", True))
        self.hud_startup_cb.setStyleSheet("color: white;")
        hud_layout.addWidget(self.hud_startup_cb)

        hud_layout.addWidget(QLabel("Interface Opacity"))
        self.opacity_slider = ModernSlider(); self.opacity_slider.setRange(20, 100); self.opacity_slider.setValue(int(config_manager.get("hud_opacity", 0.92) * 100))
        self.opacity_slider.valueChanged.connect(lambda v: self.hud.setWindowOpacity(v/100.0))
        hud_layout.addWidget(self.opacity_slider)
        
        btn_row = QHBoxLayout()
        self.show_hud_btn = QPushButton("Show HUD")
        self.show_hud_btn.clicked.connect(self.hud.show_hud)
        self.hide_hud_btn = QPushButton("Hide HUD")
        self.hide_hud_btn.clicked.connect(self.hud.hide_hud)
        self.reset_hud_btn = QPushButton("Reset Position")
        self.reset_hud_btn.clicked.connect(self.hud.reset_position)
        btn_row.addWidget(self.show_hud_btn); btn_row.addWidget(self.hide_hud_btn); btn_row.addWidget(self.reset_hud_btn)
        hud_layout.addLayout(btn_row)
        
        self.pos_lbl = QLabel(f"Position: {self.hud.x()}, {self.hud.y()}")
        self.size_lbl = QLabel(f"Size: {self.hud.width()} × {self.hud.height()}")
        self.pos_lbl.setStyleSheet("color: #a0aec0; font-size: 10px;")
        self.size_lbl.setStyleSheet("color: #a0aec0; font-size: 10px;")
        hud_layout.addWidget(self.pos_lbl); hud_layout.addWidget(self.size_lbl)
        
        self.scanline_cb = QCheckBox("Show scan line animation")
        self.scanline_cb.setChecked(config_manager.get("hud_scanline", True))
        self.scanline_cb.setStyleSheet("color: white;")
        hud_layout.addWidget(self.scanline_cb)
        
        self.corners_cb = QCheckBox("Show corner accents")
        self.corners_cb.setChecked(config_manager.get("hud_corners", True))
        self.corners_cb.setStyleSheet("color: white;")
        hud_layout.addWidget(self.corners_cb)
        
        hud_layout.addStretch(); self.pages.addWidget(hud_page)


        sys_page = QWidget(); sys_layout = QVBoxLayout(sys_page); sys_layout.addWidget(self.create_header("SYSTEM SETTINGS"))
        self.hotkey_input = self.create_input("Toggle Hotkey", config_manager.get("hotkey", "win+shift+s"))
        self.exit_hotkey_input = self.create_input("Exit Hotkey", config_manager.get("exit_hotkey", "ctrl+shift+q"))
        self.weather_input = self.create_input("Weather API Key", config_manager.get("api_keys.openweathermap"))
        self.autostart_cb = QCheckBox("Start with Windows"); self.autostart_cb.setChecked(config_manager.get("autostart", False)); self.autostart_cb.setStyleSheet("color: white;")
        sys_layout.addWidget(self.hotkey_input); sys_layout.addWidget(self.exit_hotkey_input); sys_layout.addWidget(self.weather_input); sys_layout.addWidget(self.autostart_cb); sys_layout.addStretch(); self.pages.addWidget(sys_page)

    def create_header(self, text):
        lbl = QLabel(text); lbl.setStyleSheet("color: #FFFFFF; font-family: 'Orbitron'; font-size: 18px; font-weight: bold; border-bottom: 2px solid #00FF9D; padding-bottom: 5px;"); return lbl

    def create_input(self, label, value, password=False):
        widget = QWidget(); layout = QVBoxLayout(widget); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(5)
        lbl = QLabel(label); lbl.setStyleSheet("color: #A0AAB4; font-size: 12px;"); layout.addWidget(lbl)
        edit = QLineEdit(str(value))
        if password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setStyleSheet("QLineEdit { background: rgba(255, 255, 255, 0.05); border: 1px solid #1A2634; border-radius: 5px; color: #FFFFFF; padding: 10px; } QLineEdit:focus { border-color: #00FF9D; }")
        layout.addWidget(edit); widget.input_field = edit; return widget


    def title_press(self, event): self._old_pos = event.globalPosition().toPoint()
    def title_move(self, event):
        if self._old_pos: delta = event.globalPosition().toPoint() - self._old_pos; self.move(self.x() + delta.x(), self.y() + delta.y()); self._old_pos = event.globalPosition().toPoint()

    def save(self):
        config_manager.set("wake_word", self.wake_input.input_field.text().lower())
        config_manager.set("hotkey", self.hotkey_input.input_field.text().lower())
        config_manager.set("exit_hotkey", self.exit_hotkey_input.input_field.text().lower())
        config_manager.set("hud_opacity", self.opacity_slider.value() / 100.0)
        config_manager.set("hud_visible_on_start", self.hud_startup_cb.isChecked())
        config_manager.set("hud_scanline", self.scanline_cb.isChecked())
        config_manager.set("hud_corners", self.corners_cb.isChecked())
        config_manager.set("api_keys.openrouter", self.openrouter_input.input_field.text())
        config_manager.set("api_keys.openai", self.openai_input.input_field.text())
        config_manager.set("api_keys.openweathermap", self.weather_input.input_field.text())
        config_manager.set("autostart", self.autostart_cb.isChecked())
        
        self.hud.setWindowOpacity(config_manager.get("hud_opacity"))
        self._handle_autostart(self.autostart_cb.isChecked())
        self.save_btn.setText("SAVED ✓"); QTimer.singleShot(2000, lambda: self.save_btn.setText("SAVE CHANGES"))

    def _handle_autostart(self, enabled):
        if sys.platform != "win32": return
        import winreg; key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"; app_name = "ShadowAssistant"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                cmd = f'"{sys.executable}"' if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e: print(f"Autostart error: {e}")

    def showEvent(self, event):
        screen = self.screen().availableGeometry(); self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
        self.pos_lbl.setText(f"Position: {self.hud.x()}, {self.hud.y()}")
        self.size_lbl.setText(f"Size: {self.hud.width()} × {self.hud.height()}")
        super().showEvent(event)
