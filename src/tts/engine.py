import torch
import sounddevice as sd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

class TTSEngine:
    def __init__(self):
        self.sample_rate = 48000
        self.current_audio: Optional[np.ndarray] = None
        self.stream = None
        sd.default.samplerate = self.sample_rate
        
    def synthesize(self, text: str, model_name: str = "v3_ru", speaker: str = "aidar") -> Tuple[np.ndarray, int]:
        model = torch.hub.load(
            'snakers4/silero-models',
            'silero_tts',
            language='ru',
            speaker=model_name
        )
        audio = model.apply_tts(text=text, speaker=speaker)
        self.current_audio = audio.numpy()
        return self.current_audio, self.sample_rate

    def play(self):
        if self.current_audio is not None:
            self.stream = sd.play(self.current_audio)

    def stop(self):
        sd.stop()

    def save_wav(self, filename: str):
        import soundfile as sf
        sf.write(filename, self.current_audio, self.sample_rate)

    def get_audio_level(self) -> float:
        if self.current_audio is None:
            return 0.0
        return float(np.abs(self.current_audio).mean() * 100
