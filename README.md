<img src="./assets/voxiom256.png" alt="Alt" width="256" height="256">

# Voxiom TTS GUI

A text-to-speech application using Silero TTS models with a modern GUI.

## Features
- Multiple voice models (English, Russian)
- SSML support for Russian (v4_ru model)
- Preset management
- Real-time audio visualization

## Quick Start

### Windows
1. Double-click `run_tts.bat` ( create shortcut, set voxiom.ico from "assets" folder )
2. The script will:
   - Check Python installation
   - Create a virtual environment
   - Install dependencies
   - Launch the application

### Linux
```bash
# Install dependencies
sudo apt-get install python3 python3-pip python3-venv portaudio19-dev ffmpeg

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run the application
python main.py
```

## Credits
- **Silero TTS Engine** - [github.com/snakers4/silero-models](https://github.com/snakers4/silero-models)
- **CustomTkinter UI Framework** - [github.com/TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- Developed by Voxiom TTS Team

### Silero Models Citation
```
@misc{Silero Models,
    author = {Silero Team},
    title = {Silero Models: pre-trained enterprise-grade STT/TTS models},
    year = {2021},
    publisher = {GitHub},
    howpublished = {\url{https://github.com/snakers4/silero-models}}
}
```

Note: First run will download TTS models (200-500MB) automatically.
