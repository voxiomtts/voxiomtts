import torch
import sounddevice as sd
from typing import Optional

class TTSEngine:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.sample_rate = 48000
        self._init_audio_backend()

    def _init_audio_backend(self):
        """Initialize audio system with fallback logic"""
        sd.default.samplerate = self.sample_rate
        sd.default.channels = 1
        
    def synthesize(self, text: str, model_name: str = 'v3_ru'):
        """Generate and immediately play audio"""
        audio = self._generate_audio(text, model_name)
        self._play_audio(audio)

    def _generate_audio(self, text: str, model_name: str):
        """Core TTS generation (kept separate for future PortAudio integration)"""
        model = torch.hub.load(
            'snakers4/silero-models',
            'silero_tts',
            language='ru',
            speaker=model_name
        ).to(self.device)
        return model.apply_tts(text=text)

    def _play_audio(self, audio_tensor):
        """Universal playback method (sounddevice now, PortAudio later)"""
        audio_np = audio_tensor.cpu().numpy()
        sd.play(audio_np, blocking=True)
        
    def export_wav(self, audio_tensor, filename: str):
        """For saving files without PortAudio"""
        import soundfile as sf
        sf.write(filename, audio_tensor.numpy(), self.sample_rate)
