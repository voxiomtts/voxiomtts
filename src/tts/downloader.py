import os
import requests
from pathlib import Path
from PySide6.QtCore import QObject, Signal

class ModelDownloader(QObject):
    progress_updated = Signal(int, int)  # current, total
    download_finished = Signal(str)      # model_path
    download_failed = Signal(str)        # error_msg

    def __init__(self):
        super().__init__()
        self.models = {
            'v3_1_ru': 'https://models.silero.ai/models/tts/ru/v3_1_ru.pt',
            'v4_ru': 'https://models.silero.ai/models/tts/ru/v4_ru.pt'
        }
        os.makedirs('models/silero', exist_ok=True)

    def download_model(self, model_name):
        try:
            url = self.models[model_name]
            local_path = Path(f'models/silero/{model_name}.pt')
            
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress_updated.emit(downloaded, total_size)
            
            self.download_finished.emit(str(local_path))
        except Exception as e:
            self.download_failed.emit(str(e))
