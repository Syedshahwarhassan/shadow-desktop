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
