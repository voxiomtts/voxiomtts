import os
import torch
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play

def check_gpu():
    """Returns GPU status string for logging."""
    if torch.cuda.is_available():
        return f"GPU: {torch.cuda.get_device_name(0)} (CUDA {torch.version.cuda})"
    return "No GPU detected. Using CPU."

def validate_text(text: str) -> bool:
    """Check if text is valid for TTS."""
    return len(text.strip()) > 0

def save_audio(audio, filename: str, sample_rate: int = 48000):
    """Save audio to outputs/ folder."""
    os.makedirs("outputs", exist_ok=True)
    sf.write(f"outputs/{filename}", audio, sample_rate)

def play_audio(audio, sample_rate: int = 48000):
    """Play audio using pydub."""
    audio_segment = AudioSegment(
        audio.tobytes(),
        frame_rate=sample_rate,
        sample_width=audio.dtype.itemsize,
        channels=1
    )
    play(audio_segment)
