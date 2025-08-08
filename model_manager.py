# model_manager.py
import os
import hashlib
import requests
from pathlib import Path
from omegaconf import OmegaConf
from typing import Dict, List, Optional

class ModelManager:
    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.models_yml_url = "https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml"
        self.local_models_yml = self.models_dir / "models.yml"
        self.tts_models = []
        self.available_models = {}

    def fetch_models_yml(self) -> bool:
        """Download the latest models.yml from Silero repo"""
        try:
            response = requests.get(self.models_yml_url)
            response.raise_for_status()
            with open(self.local_models_yml, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Failed to fetch models.yml: {e}")
            return False

    def load_models_config(self) -> Dict:
        """Load models config from local YAML"""
        try:
            if not self.local_models_yml.exists():
                if not self.fetch_models_yml():
                    return {}

            config = OmegaConf.load(self.local_models_yml)
            self.tts_models = [
                model for model in config.tts_models
                if not model.get('disabled', False)
            ]
            return config
        except Exception as e:
            print(f"Error loading models config: {e}")
            return {}

    def scan_for_models(self) -> Dict[str, dict]:
        """Check which models are actually downloaded"""
        self.available_models = {}
        for model in self.tts_models:
            model_file = self.models_dir / model.file
            if model_file.exists():
                self.available_models[model.name] = OmegaConf.to_container(model)
        return self.available_models

    def verify_model(self, model_name: str) -> bool:
        """Verify model integrity if hash is provided"""
        if model_name not in self.available_models:
            return False

        model = self.available_models[model_name]
        if 'sha256' not in model:
            return True  # No hash to verify against

        model_path = self.models_dir / model['file']
        try:
            with open(model_path, 'rb') as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            return actual_sha.lower() == model['sha256'].lower()
        except Exception as e:
            print(f"Verification failed for {model_name}: {e}")
            return False

    def get_model_file(self, model_name: str) -> Optional[Path]:
        """Get path to model file if available"""
        if model_name in self.available_models:
            return self.models_dir / self.available_models[model_name]['file']
        return None
