import os
import shutil
import socket
import requests
import psutil
import datetime
import pyautogui
from ai_brain import ai_brain
from googletrans import Translator
from config_manager import config_manager

class AdvancedCommands:
    @staticmethod
    def get_ip_info():
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            public_ip = requests.get('https://api.ipify.org').text
            return f"Your Local IP is {local_ip} and Public IP is {public_ip}."
        except Exception as e:
            return f"Error fetching IP info: {e}"

    @staticmethod
    def run_speed_test():
        try:
            import speedtest
            print("[CMD] Running speed test...")
            st = speedtest.Speedtest()
            st.get_best_server()
            download_speed = st.download() / 1_000_000
            upload_speed = st.upload() / 1_000_000
            return f"Speed Test Results: Download {download_speed:.2f} Mbps, Upload {upload_speed:.2f} Mbps."
        except Exception as e:
            print(f"[ERR] Speedtest: {e}")
            return "Speed test failed. Please make sure you have internet access."

    @staticmethod
    def get_system_health():
        try:
            battery = psutil.sensors_battery()
            uptime = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            cpu_count = psutil.cpu_count()
            
            health_report = f"System Uptime: {uptime}. "
            if battery:
                health_report += f"Battery: {battery.percent}% {'(Charging)' if battery.power_plugged else '(Discharging)'}. "
            health_report += f"CPU Cores: {cpu_count}."
            return health_report
        except Exception as e:
            return f"Error fetching system health: {e}"

    @staticmethod
    def translate_text(text, target_lang='ur'):
        try:
            translator = Translator()
            # If target_lang is 'ur', we translate to Urdu, else to English
            translation = translator.translate(text, dest=target_lang)
            return f"Translation: {translation.text}"
        except Exception as e:
            return f"Translation failed: {e}"

    @staticmethod
    def organize_folder(folder_path):
        if not os.path.exists(folder_path):
            return "Folder does not exist."
            
        extensions = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
            'Videos': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'],
            'Documents': ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.pptx', '.csv', '.rtf'],
            'Music': ['.mp3', '.wav', '.flac', '.m4a', '.aac'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'Executables': ['.exe', '.msi', '.bat', '.sh'],
            'Shortcuts': ['.lnk', '.url'],
            'Installers': ['.iso', '.dmg', '.pkg']
        }
        
        count = 0
        moved_anything = False
        
        # 1. Move files
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            
            # Skip directories we created or existing ones
            if os.path.isdir(filepath):
                continue
                
            file_ext = os.path.splitext(filename)[1].lower()
            target_category = "Other"
            
            for folder_name, exts in extensions.items():
                if file_ext in exts:
                    target_category = folder_name
                    break
            
            dest_folder = os.path.join(folder_path, target_category)
            os.makedirs(dest_folder, exist_ok=True)
            
            # Handle duplicate filenames
            base_name, ext = os.path.splitext(filename)
            dest_path = os.path.join(dest_folder, filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_folder, f"{base_name} ({counter}){ext}")
                counter += 1
            
            try:
                shutil.move(filepath, dest_path)
                count += 1
                moved_anything = True
            except Exception as e:
                print(f"[ERR] Failed to move {filename}: {e}")
        
        # 2. Cleanup empty directories (optional but good for 'safai')
        if moved_anything:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path) and not os.listdir(item_path):
                    try:
                        os.rmdir(item_path)
                    except:
                        pass
        
        return f"Safai mukammal! {count} files ko organize kar diya gaya hai {os.path.basename(folder_path)} mein."

    @staticmethod
    def close_app(app_name):
        app_name = app_name.lower()
        count = 0
        for proc in psutil.process_iter(['name']):
            try:
                if app_name in proc.info['name'].lower():
                    proc.terminate()
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if count > 0:
            return f"Closed {count} instances of {app_name}."
        return f"No running app found with name {app_name}."

    @staticmethod
    def clean_temp_files():
        temp_paths = [
            os.environ.get('TEMP'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
        ]
        
        deleted_count = 0
        error_count = 0
        
        for path in temp_paths:
            if not path or not os.path.exists(path):
                continue
            
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        deleted_count += 1
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        deleted_count += 1
                except Exception:
                    # Files in use cannot be deleted, which is normal
                    error_count += 1
        
        return f"Safai mukammal! {deleted_count} temporary files ko delete kar diya gaya hai. ({error_count} files in-use thi aur delete nahi ho sakeen)."

    @staticmethod
    def check_port(port):
        try:
            port = int(port)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    return f"Port {port} is open and active."
                else:
                    return f"Port {port} is closed or not in use."
        except Exception as e:
            return f"Error checking port: {e}"

    @staticmethod
    def get_motivation():
        quotes = [
            "Your limitation—it's only your imagination.",
            "Push yourself, because no one else is going to do it for you.",
            "Sometimes later becomes never. Do it now.",
            "Great things never come from comfort zones.",
            "Dream it. Wish it. Do it.",
            "Success doesn’t just find you. You have to go out and get it.",
            "The harder you work for something, the greater you’ll feel when you achieve it.",
            "Dream bigger. Do bigger.",
            "Don’t stop when you’re tired. Stop when you’re done.",
            "Wake up with determination. Go to bed with satisfaction."
        ]
        import random
        return random.choice(quotes)

    @staticmethod
    def todo_manager(action, task=None):
        import json
        todo_file = "todo.json"
        
        # Load existing tasks
        if os.path.exists(todo_file):
            with open(todo_file, "r") as f:
                try:
                    tasks = json.load(f)
                except:
                    tasks = []
        else:
            tasks = []
            
        if action == "add" and task:
            tasks.append({"task": task, "done": False, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
            with open(todo_file, "w") as f:
                json.dump(tasks, f)
            return f"Task added: {task}"
            
        elif action == "list":
            if not tasks:
                return "Your to-do list is empty."
            res = "Your tasks:\n"
            for i, t in enumerate(tasks):
                status = "✓" if t["done"] else "○"
                res += f"{i+1}. {status} {t['task']}\n"
            return res
            
        elif action == "clear":
            with open(todo_file, "w") as f:
                json.dump([], f)
            return "To-do list cleared."
            
        elif action == "done" and task:
            try:
                idx = int(task) - 1
                if 0 <= idx < len(tasks):
                    tasks[idx]["done"] = True
                    with open(todo_file, "w") as f:
                        json.dump(tasks, f)
                    return f"Marked task {idx+1} as done."
            except:
                pass
            return "Task not found."

    @staticmethod
    def start_pomodoro():
        # This will be handled by the dispatcher using TimerCommands for 25 mins
        return "Starting Pomodoro session. 25 minutes of focus starts now!"

    @staticmethod
    def clipboard_action(action, text=None):
        import pyperclip
        if action == "set" and text:
            pyperclip.copy(text)
            return "Text copied to clipboard."
        elif action == "get":
            val = pyperclip.paste()
            if val:
                return f"Clipboard contains: {val}"
            return "Clipboard is empty."
        return "Invalid clipboard action."

    @staticmethod
    def window_control(action):
        import ctypes
        # Get active window handle
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        if action == "maximize":
            ctypes.windll.user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
            return "Window maximized."
        elif action == "minimize":
            ctypes.windll.user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
            return "Window minimized."
        elif action == "close":
            ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0) # WM_CLOSE
            return "Window closed."
        elif action == "minimize_all":
            ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0) # Win Key Down
            ctypes.windll.user32.keybd_event(0x44, 0, 0, 0) # D Key Down
            ctypes.windll.user32.keybd_event(0x44, 0, 2, 0) # D Key Up
            ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0) # Win Key Up
            return "Minimizing all windows."
        return "Unknown window action."

    @staticmethod
    def search_and_open_file(filename):
        print(f"[CMD] Searching for file '{filename}' in D: drive...")
        filename = filename.strip()
        
        try:
            # Fast search using cmd 'dir'
            command = f'dir "D:\\*{filename}*" /S /B'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.stdout:
                # Get the first match
                first_match = result.stdout.strip().split('\n')[0].strip()
                if os.path.exists(first_match):
                    print(f"[CMD] Found: {first_match}")
                    os.startfile(first_match)
                    return f"Opening file {os.path.basename(first_match)}."
            
            return f"I couldn't find a file named {filename} in your D drive."
        except Exception as e:
            print(f"[ERR] Search file: {e}")
            return "An error occurred while searching for the file."

    @staticmethod
    def analyze_screen(prompt="Describe this screen."):
        try:
            print("[CMD] Capturing screen for analysis...")
            path = "screen_analysis.png"
            pyautogui.screenshot(path)
            result = ai_brain.analyze_image(path, prompt)
            # Cleanup
            if os.path.exists(path):
                os.remove(path)
            return result
        except Exception as e:
            return f"Screen analysis failed: {e}"

    @staticmethod
    def autonomous_research(topic):
        from .extra_cmds import WikipediaCommands
        print(f"[CMD] Starting autonomous research on: {topic}")
        
        # 1. Get Wikipedia Data
        wiki_data = WikipediaCommands.summary(topic, sentences=10)
        if "couldn't find" in wiki_data or "failed" in wiki_data:
            # Try AI search
            wiki_data = ai_brain.get_response(f"Research and give me detailed info about {topic}")
            
        # 2. AI Synthesis
        report_prompt = f"Write a professional research report about {topic} based on this data: {wiki_data}. Format with headers."
        report = ai_brain.get_response(report_prompt)
        
        # 3. Save to file
        import winshell
        docs = winshell.folder("personal")
        path = os.path.join(docs, f"{topic.replace(' ', '_')}_Research.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
            
        return f"Research complete. Report saved to your Documents as {topic}_Research.txt."

    @staticmethod
    def mouse_control(action, amount=100):
        try:
            amount = int(amount)
            if action == "up":
                pyautogui.moveRel(0, -amount)
            elif action == "down":
                pyautogui.moveRel(0, amount)
            elif action == "left":
                pyautogui.moveRel(-amount, 0)
            elif action == "right":
                pyautogui.moveRel(amount, 0)
            elif action == "click":
                pyautogui.click()
            elif action == "double click":
                pyautogui.doubleClick()
            return f"Mouse moved {action}."
        except:
            return "Mouse control failed."

    @staticmethod
    def set_app_volume(app_name, volume_level):
        """Set volume for a specific application (0.0 to 1.0)."""
        try:
            from pycaw.pycaw import AudioUtilities
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                volume = session.SimpleAudioVolume
                if session.Process and session.Process.name().lower() == f"{app_name.lower()}.exe":
                    volume.SetMasterVolume(float(volume_level), None)
                    return f"Volume for {app_name} set to {int(volume_level * 100)}%."
            return f"Could not find a running process for {app_name}."
        except Exception as e:
            return f"App volume control failed: {e}"

    @staticmethod
    def send_email(recipient, subject, contents):
        """Send a basic email using yagmail (requires credentials in config)."""
        try:
            import yagmail
            user = config_manager.get("credentials.gmail_email")
            password = config_manager.get("credentials.gmail_password")
            
            if not user or not password:
                return "Email credentials missing. Please add gmail_email and gmail_password to config.json."
            
            yag = yagmail.SMTP(user, password)
            yag.send(to=recipient, subject=subject, contents=contents)
            return f"Email successfully sent to {recipient}."
        except Exception as e:
            return f"Failed to send email: {e}"
