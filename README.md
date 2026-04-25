# AntiGravity - JARVIS Style Voice Assistant

AntiGravity is a production-grade Python desktop voice assistant with a high-fidelity, hardware-accelerated circular HUD.

## Features
- **Always-on-top Circular HUD**: Animated rings and arcs with glowing effects, providing real-time visual feedback for Idle, Listening, and Speaking states.
- **System Tray Integration**: Background operation with toggleable visibility, settings, and robust restart capability.
- **Bilingual Command Processing**: Advanced Urdu-English hybrid parsing with specialized normalizations (e.g., handling reversed Urdu word order and STT variations).
- **System Control**: Volume control, brightness adjustment, shutdown/restart/lock PC with custom timers.
- **App & File Management**: Intelligently open apps (VS Code, Spotify, File Explorer, Task Manager) and search/open specific folders dynamically.
- **Desktop Automation**: Take screenshots, create folders and files, manage recycle bin, and take quick text notes.
- **Dictation & Typing Mode**: Voice-to-text dictation across the OS, along with keyboard shortcut emulation (copy, paste, undo, redo, etc.).
- **Media & Navigation**: Hands-free scrolling and direct media playback on YouTube and Spotify.
- **WhatsApp Integration**: Send WhatsApp messages using natural language and manage local contacts.
- **Developer Tools**: Voice-activated project scaffolding (React, Next.js, Python, .NET, etc.), AI code generation, and Git status checks.
- **Productivity & Utilities**: Check real-time weather, stock/crypto prices, get the time, hear jokes, and receive motivational quotes.
- **AI Brain Fallback**: Integrated with OpenRouter (using models like OpenAI GPT-4o-mini) for general inquiries and intelligent conversational responses.

## Installation

1. **Clone the repository** (or copy the files).
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure API Keys**:
   Open `config.json` and add your OpenAI and OpenWeatherMap API keys.
4. **Run the assistant**:
   ```bash
   python main.py
   ```

## Key Commands
Here are some examples of what you can ask (in English or Urdu):
- **System**: "Hey Gravity, system info", "Hey Gravity, lock PC", "Hey Gravity, shutdown in 60 seconds", "awaaz barhaao" (Volume up)
- **Apps & Navigation**: "Hey Gravity, open VS Code", "Hey Gravity, search folder projects", "Hey Gravity, scroll down"
- **Dictation**: "Hey Gravity, start typing", "Hey Gravity, dictation off"
- **Media**: "Hey Gravity, play Interstellar theme on YouTube", "Hey Gravity, bajao"
- **Dev**: "Hey Gravity, create a React project named portfolio", "Hey Gravity, code a python login script"
- **Messaging**: "Hey Gravity, mama ko WhatsApp message bhejo"
- **Utilities**: "Hey Gravity, what is the weather in London?", "Hey Gravity, tell me a joke", "Hey Gravity, apple stock price"
## Project Structure
- `main.py`: Orchestrator and entry point.
- `hud.py`: PyQt6 HUD implementation.
- `listener.py`: Speech recognition thread.
- `commands/`: Modular command plugins.
- `tray.py`: System tray integration.
- `config_manager.py`: Configuration persistence.

## License
MIT
