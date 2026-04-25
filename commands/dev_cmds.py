import subprocess
import os

class DevCommands:
    @staticmethod
    def open_vscode(path="."):
        try:
            subprocess.Popen(["code", path], shell=True)
            return "Opening VS Code."
        except:
            return "VS Code not found in PATH."

    @staticmethod
    def git_status():
        try:
            res = subprocess.check_output(["git", "status"], stderr=subprocess.STDOUT).decode()
            return "Git status retrieved."
        except:
            return "Not a git repository."

    @staticmethod
    def run_python(filename):
        try:
            subprocess.Popen(["python", filename], shell=True)
            return f"Running {filename}."
        except:
            return f"Failed to run {filename}."

    @staticmethod
    def create_project_starter(framework, project_name):
        framework = framework.lower().strip()
        project_name = project_name.replace(" ", "-").lower() or "my-project"
        
        try:
            import winshell
            import os
            import subprocess
            desktop = winshell.desktop()
            
            cmd = None
            if "react" in framework and "native" not in framework:
                cmd = f"npx create-react-app {project_name}"
            elif "next" in framework:
                cmd = f"npx create-next-app@latest {project_name} --use-npm --eslint --tailwind --app --src-dir --import-alias \"@/*\""
            elif "vue" in framework:
                cmd = f"npm create vue@latest {project_name}"
            elif "angular" in framework:
                cmd = f"npx @angular/cli new {project_name} --defaults"
            elif "svelte" in framework:
                cmd = f"npm create svelte@latest {project_name}"
            elif "vite" in framework:
                cmd = f"npm create vite@latest {project_name} -- --template react"
            elif "net" in framework or "dotnet" in framework:
                cmd = f"dotnet new webapp -n {project_name}"
            elif "node" in framework or "express" in framework:
                cmd = f"npx express-generator {project_name}"
            elif "django" in framework:
                cmd = f"django-admin startproject {project_name}"
            else:
                return f"ارے، مجھے {framework} کا پروجیکٹ بنانا نہیں آتا۔"

            if cmd:
                print(f"[CMD] Running starter: {cmd} in {desktop}")
                # Use start cmd /k to keep the window open so the user can see progress
                subprocess.Popen(f"start cmd /k \"echo Creating {framework} project '{project_name}'... && {cmd}\"", shell=True, cwd=desktop)
                return f"بالکل! میں {framework} کا پروجیکٹ {project_name} کے نام سے ڈیسک ٹاپ پر بنا رہی ہوں۔ کمانڈ پرامپٹ چیک کریں!"
        except Exception as e:
            return f"پروجیکٹ بنانے میں مسئلہ ہو گیا: {str(e)}"

    @staticmethod
    def scaffold_project(prompt):
        from ai_brain import ai_brain
        import re
        import time
        import winshell

        print(f"[CMD] Scaffolding project: '{prompt}'")
        raw_output = ai_brain.generate_code(prompt)

        if not raw_output:
            return "Failed to generate code. Please check your AI core connection."

        try:
            desktop = winshell.desktop()
            timestamp = time.strftime("%H%M%S")
            project_dir = os.path.join(desktop, f"Shadow_Project_{timestamp}")
            os.makedirs(project_dir, exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Could not create project directory: {e}")
            return "Failed to create project directory."

        # Parse markdown for filenames and code blocks
        pattern = re.compile(r'(?:`([^`]+)`\s*)?```[\w]*\n(.*?)```', re.DOTALL)
        matches = pattern.findall(raw_output)

        if not matches:
            # Fallback if no code blocks were formatted correctly
            path = os.path.join(project_dir, "main.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw_output)
        else:
            file_count = 0
            for filename, code in matches:
                if not filename:
                    file_count += 1
                    filename = f"file_{file_count}.txt"
                filename = os.path.basename(filename) # Sanitize path
                path = os.path.join(project_dir, filename)
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(code.strip() + "\n")
                except Exception as e:
                    print(f"[ERROR] Failed to write {filename}: {e}")

        DevCommands.open_vscode(project_dir)
        return "Project created and opened in VS Code."
