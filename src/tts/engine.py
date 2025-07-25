import torch
from pathlib import Path

class TTSEngine:
    def __init__(self):
        self.device = torch.device('cpu')
        self.models = {
            'v3_1_ru': 'models/silero/v3_1_ru.pt',
            'v4_ru': 'models/silero/v4_ru.pt'
        }
        self.speakers = {'aidar', 'baya', 'kseniya', 'xenia'}
        self.sample_rate = 48000
        
    def load_model(self, model_name):
        model_path = Path(self.models[model_name])
        if not model_path.exists():
            raise FileNotFoundError(f"Model {model_name} not found at {model_path}")
        
        torch.set_num_threads(4)
        model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language='ru',
            speaker=model_name
        )
        return model.to(self.device)
    
    def synthesize(self, text, voice):
        model = self.load_model(voice)
        audio = model.apply_tts(text=text, speaker=random.choice(self.speakers))
        # TODO: Add audio playback
        return audio
