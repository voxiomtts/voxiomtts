import torch
import random
from pathlib import Path
from .player import AudioPlayer

class TTSEngine:
    def __init__(self):
        self.device = torch.device('cpu')
        self.player = AudioPlayer()
        self.loaded_model = None
        
    def load_model(self, model_name):
        model_path = Path(f'models/silero/{model_name}.pt')
        if not model_path.exists():
            raise FileNotFoundError(f"Model {model_name} not found")
        
        torch.set_num_threads(4)
        model = torch.package.PackageImporter(model_path).load_pickle("tts_models", "model")
        self.loaded_model = model.to(self.device)
        return self.loaded_model
    
    def synthesize(self, text, speaker):
        if not self.loaded_model:
            raise RuntimeError("No model loaded")
        
        audio = self.loaded_model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=48000,
            put_accent=True,
            put_yo=True
        )
        return audio
