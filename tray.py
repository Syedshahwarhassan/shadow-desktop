import pystray
from PIL import Image, ImageDraw
from PyQt6.QtCore import QThread, pyqtSignal
import threading

class TrayIcon:
    def __init__(self, hud, app):
        self.hud = hud
        self.app = app
        self.icon = None
        self.thread = threading.Thread(target=self._run_tray, daemon=True)

    def _create_image(self):
        # Create a simple icon image
        image = Image.new('RGB', (64, 64), (5, 10, 15))
        dc = ImageDraw.Draw(image)
        dc.ellipse([10, 10, 54, 54], outline=(0, 212, 255), width=4)
        return image

    def _run_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Show/Hide', self._toggle_hud),
            pystray.MenuItem('Settings', self._open_settings),
            pystray.MenuItem('Restart', self._restart),
            pystray.MenuItem('Exit', self._exit)
        )
        self.icon = pystray.Icon("AntiGravity", self._create_image(), "AntiGravity", menu)
        self.icon.run()

    def start(self):
        self.thread.start()

    def _toggle_hud(self):
        if self.hud.isVisible():
            self.hud.hide()
        else:
            self.hud.show()

    def _open_settings(self):
        print("Settings not implemented yet")

    def _restart(self):
        import sys
        import subprocess
        self.icon.stop()
        self.app.quit()
        # Restarts the application whether it's a script or an executable
        if getattr(sys, 'frozen', False):
            # Running as compiled PyInstaller executable
            args = [sys.executable] + sys.argv[1:]
        else:
            # Running as a Python script
            args = [sys.executable] + sys.argv
        subprocess.Popen(args)
        sys.exit()

    def _exit(self):
        self.icon.stop()
        self.app.quit()
