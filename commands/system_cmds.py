import subprocess
import psutil
import ctypes
import os
import webbrowser

# Warm up psutil so subsequent non-blocking calls return real numbers
# instantly instead of zero. This trades a tiny one-time cost for big
# per-call savings (saves ~500ms on every "system info" command).
psutil.cpu_percent(interval=None)


class SystemCommands:

    @staticmethod
    def get_system_info():
        # Non-blocking sample (uses delta since the previous call → instant).
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        # Disk path differs by OS; pick the right one rather than crashing on Linux.
        disk_path = 'C:/' if os.name == 'nt' else '/'
        try:
            disk = psutil.disk_usage(disk_path).percent
        except Exception:
            disk = 0
        info = f"CPU {cpu}%, RAM {ram}%, Disk {disk}%"
        print(f"[CMD] System Info → {info}")
        return f"System Status: CPU {cpu} percent, RAM {ram} percent, Disk {disk} percent."

    @staticmethod
    def set_volume(change):
        try:
            key = 0xAF if change > 0 else 0xAE  # VK_VOLUME_UP / VK_VOLUME_DOWN
            steps = abs(change) // 2
            for _ in range(steps):
                ctypes.windll.user32.keybd_event(key, 0, 0, 0)
                ctypes.windll.user32.keybd_event(key, 0, 2, 0)  # key up
            direction = "up" if change > 0 else "down"
            print(f"[CMD] Volume {direction} by {steps} steps")
            return f"Volume {'increased' if change > 0 else 'decreased'}."
        except Exception as e:
            print(f"[ERR] Volume: {e}")
            return "Could not adjust volume."

    @staticmethod
    def set_brightness(level):
        level = max(0, min(100, int(level)))
        # Try screen_brightness_control first
        try:
            from screen_brightness_control import set_brightness as _set
            _set(level)
            print(f"[CMD] Brightness → {level}% (sbc)")
            return f"Brightness set to {level} percent."
        except Exception:
            pass
        # Fallback: PowerShell WMI brightness command
        try:
            script = (
                f"$b = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods;"
                f"$b.WmiSetBrightness(1, {level})"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                 "-NonInteractive", "-Command", script],
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print(f"[CMD] Brightness → {level}% (powershell)")
            return f"Brightness set to {level} percent."
        except Exception as e:
            print(f"[ERR] Brightness: {e}")
            return "Could not set brightness on this display."

    @staticmethod
    def lock_screen():
        print("[CMD] Locking screen...")
        ctypes.windll.user32.LockWorkStation()
        return "Screen locked."

    @staticmethod
    def shutdown(timer=30):
        print(f"[CMD] Shutdown in {timer}s")
        subprocess.Popen(["shutdown", "/s", "/t", str(timer)])
        return f"Shutting down in {timer} seconds."

    @staticmethod
    def restart(timer=30):
        print(f"[CMD] Restart in {timer}s")
        subprocess.Popen(["shutdown", "/r", "/t", str(timer)])
        return f"Restarting in {timer} seconds."

    @staticmethod
    def open_app(app_name):
        app_name = app_name.lower().strip()
        print(f"[CMD] Open app request: '{app_name}'")

        # --- Web-based apps (open in browser directly) ---
        web_apps = {
            "youtube":    "https://www.youtube.com",
            "tiktok":     "https://www.tiktok.com",
            "instagram":  "https://www.instagram.com",
            "facebook":   "https://www.facebook.com",
            "twitter":    "https://www.twitter.com",
            "whatsapp":   "https://web.whatsapp.com",
            "gmail":      "https://mail.google.com",
            "google":     "https://www.google.com",
            "github":     "https://www.github.com",
            "netflix":    "https://www.netflix.com",
            "tiktok":"https://tiktok.com",
            "chatgpt":    "https://chat.openai.com",
            "maps":       "https://maps.google.com",
            "translate":  "https://translate.google.com",
            "calendar":   "https://calendar.google.com",
        }

        # --- Local Windows apps (executable names) ---
        local_apps = {
            "notepad":           "notepad.exe",
            "calculator":        "calc.exe",
            "paint":             "mspaint.exe",
            "file explorer":     "explorer.exe",
            "explorer":          "explorer.exe",
            "task manager":      "taskmgr.exe",
            "taskmgr":           "taskmgr.exe",
            "cmd":               "cmd.exe",
            "command prompt":    "cmd.exe",
            "settings":          "ms-settings:",
            "control panel":     "control",
            "wordpad":           "wordpad.exe",
            "snipping tool":     "SnippingTool.exe",
        }

        # --- Apps launched via Windows 'start' protocol ---
        start_apps = {
            "spotify":           "spotify",
            "discord":           "discord",
            "telegram":          "telegram",
            "steam":             "steam",
            "vscode":            "code",
            "vs code":           "code",
            "visual studio code":"code",
            "chrome":            "chrome",
            "firefox":           "firefox",
            "edge":              "msedge",
            "word":              "winword",
            "excel":             "excel",
            "powerpoint":        "powerpnt",
            "antigravity":       "antigravity",
            "anti gravity":      "antigravity"
        }

        # Check web apps
        for key, url in web_apps.items():
            if key in app_name:
                print(f"[CMD] Opening web: {url}")
                webbrowser.open(url)
                return f"Opening {key} in your browser."

        # Check local apps
        for key, exe in local_apps.items():
            if key in app_name:
                print(f"[CMD] Launching local: {exe}")
                try:
                    if exe.startswith("ms-"):
                        subprocess.Popen(["start", exe], shell=True)
                    else:
                        subprocess.Popen(exe, creationflags=subprocess.CREATE_NO_WINDOW)
                    return f"Opening {key}."
                except Exception as e:
                    print(f"[ERR] Local app: {e}")

        # Check start apps
        for key, cmd in start_apps.items():
            if key in app_name:
                print(f"[CMD] Launching via start: {cmd}")
                try:
                    subprocess.Popen(f"start {cmd}", shell=True, 
                                    creationflags=subprocess.CREATE_NO_WINDOW)
                    return f"Opening {key}."
                except Exception as e:
                    print(f"[ERR] Start app: {e}")

        # Last resort: try as raw command / URL
        print(f"[CMD] Fallback: trying raw launch for '{app_name}'")
        try:
            subprocess.Popen(app_name, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Attempting to open {app_name}."
        except:
            return f"I couldn't find or open '{app_name}'. Please add it to my app list."

    @staticmethod
    def open_file_explorer(path=None):
        target = path or "C:\\"
        print(f"[CMD] Opening File Explorer: {target}")
        subprocess.Popen(f"explorer {target}", shell=True)
        return f"Opening File Explorer."

    @staticmethod
    def search_and_open_folder(folder_name):
        print(f"[CMD] Searching for folder '{folder_name}' in D: drive...")
        folder_name = folder_name.strip()
        
        try:
            # Fast search using cmd 'dir'
            command = f'dir "D:\\*{folder_name}*" /A:D /S /B'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.stdout:
                # Get the first match
                first_match = result.stdout.strip().split('\n')[0].strip()
                if os.path.exists(first_match):
                    print(f"[CMD] Found: {first_match}")
                    subprocess.Popen(f'explorer "{first_match}"', shell=True)
                    return f"Opening folder {os.path.basename(first_match)}."
            
            return f"I couldn't find a folder named {folder_name} in your D drive."
        except Exception as e:
            print(f"[ERR] Search folder: {e}")
            return "An error occurred while searching for the folder."
