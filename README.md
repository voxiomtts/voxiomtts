# Voxiom TTS

## First-Run Setup
The app will automatically download Silero models to `models/tts/`.  
To pre-download all supported models:
```bash
python -c "from src.tts_engine import SileroTTS; SileroTTS.download_all_models()"
