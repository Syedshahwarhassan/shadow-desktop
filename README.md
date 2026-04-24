# AntiGravity - JARVIS Style Voice Assistant

AntiGravity is a production-grade Python desktop voice assistant with a high-fidelity, hardware-accelerated circular HUD.

## Features
- **Always-on-top Circular HUD**: Animated rings and arcs with glowing effects.
- **Dynamic Status Animations**: Different visual states for Idle, Listening, and Speaking.
- **System Control**: Volume, brightness, shutdown, restart, and more.
- **Productivity Tools**: Weather, news, stocks, jokes, and quotes.
- **AI Brain**: Integrated with OpenAI GPT-4o-mini for intelligent responses.
- **System Tray**: Background operation with toggleable visibility and settings.

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
- "Hey Gravity, system info"
- "Hey Gravity, volume up"
- "Hey Gravity, what is the weather in London?"
- "Hey Gravity, tell me a joke"
- "Hey Gravity, shutdown in 60 seconds"

## Project Structure
- `main.py`: Orchestrator and entry point.
- `hud.py`: PyQt6 HUD implementation.
- `listener.py`: Speech recognition thread.
- `commands/`: Modular command plugins.
- `tray.py`: System tray integration.
- `config_manager.py`: Configuration persistence.

## License
MIT
