import os
import json
import torch
from pathlib import Path
from typing import Dict, List, Optional

class SileroTTS:
    def __init__(self, models_dir: str = 'models/tts'):
        self.models_dir = os.path.normpath(models_dir)
        os.makedirs(self.models_dir, exist_ok=True)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.models = {}
        self.current_model = None

        self.supported_models = {
            "v3_en": {
                "file": "v3_en.pt",
                "sample_rates": [8000, 24000, 48000],  # Note: plural
                "speakers": [f'en_{i}' for i in range(118)],
                "default_rate": 48000
            },
            "v3_1_ru": {
                "file": "v3_1_ru.pt",
                "sample_rates": [8000, 24000, 48000],  # Note: plural
                "speakers": ['aidar', 'baya', 'kseniya', 'xenia', 'eugene', 'random'],
                "default_rate": 48000
            },
            "v4_ru": {
                "file": "v4_ru.pt",
                "sample_rates": [8000, 24000, 48000],  # Note: plural
                "speakers": ['aidar', 'baya', 'kseniya', 'xenia', 'eugene', 'random'],
                "default_rate": 48000,
                "supports_ssml": True
            }
        }

        self.presets = self._load_presets()

    def _load_presets(self) -> dict:
        presets_path = os.path.join(os.path.dirname(__file__), 'presets.json')
        default_presets = {
            "General": {
                "default": {
                    "text": "Please check your presets.json file for errors",
                    "ssml": False  # Note: Python's True/False, not JSON's true/false
                }
            }
        }

        try:
            with open(presets_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in presets file: {e}")
            return default_presets
        except Exception as e:
            print(f"Failed to load presets: {e}")
            return default_presets

    def load_model(self, model_name: str) -> bool:
        try:
            if model_name not in self.supported_models:
                raise ValueError(f"Model {model_name} not supported")

            model_path = os.path.join(self.models_dir, self.supported_models[model_name]["file"])

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")

            # Clear CUDA cache before loading
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Try standard loading first
            try:
                model = torch.jit.load(model_path, map_location=self.device)
            except Exception:
                # Fallback to PackageImporter
                importer = torch.package.PackageImporter(model_path)
                model = importer.load_pickle("tts_models", "model")

            model.to(self.device)
            self.models[model_name] = model
            self.current_model = model_name
            return True

        except Exception as e:
            print(f"Model loading failed: {str(e)}")
            return False

    def get_model_info(self, model_name: str) -> dict:
        """Get complete model configuration"""
        if model_name not in self.supported_models:
            raise ValueError(f"Model {model_name} not supported")
        return self.supported_models[model_name]

    def speak(self, text: str, speaker: str = None, ssml: bool = False) -> torch.Tensor:
        if not self.current_model:
            raise ValueError("No model loaded")

        model = self.models[self.current_model]
        config = self.supported_models[self.current_model]

        if not speaker:
            speaker = config["speakers"][0]

        # Clean and prepare text
        text = text.strip()
        if not text:
            raise ValueError("Empty text input")

        # Handle multiline text
        text = ' '.join(line.strip() for line in text.split('\n') if line.strip())

        try:
            if self.current_model == "v4_ru":
                if ssml:
                    if not text.startswith("<speak>"):
                        text = f"<speak>{text}</speak>"
                    return model.apply_tts(
                        ssml_text=text,
                        speaker=speaker,
                        sample_rate=config["default_rate"]
                    )
                else:
                    # Remove any SSML tags if not in SSML mode
                    text = text.replace("<speak>", "").replace("</speak>", "")
                    text = text.replace("<prosody", "").replace(">", "")
                    text = text.replace("<break", "").replace("/>", "")
                    return model.apply_tts(
                        text=text,
                        speaker=speaker,
                        sample_rate=config["default_rate"]
                    )
            else:  # v3 models
                # Always remove SSML tags for non-SSML models
                text = text.replace("<speak>", "").replace("</speak>", "")
                text = text.replace("<prosody", "").replace(">", "")
                text = text.replace("<break", "").replace("/>", "")
                return model.apply_tts(
                    text=text,
                    speaker=speaker,
                    sample_rate=config["default_rate"]
                )
        except Exception as e:
            raise ValueError(f"Speech generation failed: {str(e)}")

    def get_voices(self) -> List[str]:
        if not self.current_model:
            return []
        return self.supported_models[self.current_model]["speakers"]

    def supports_ssml(self) -> bool:
        return self.supported_models.get(self.current_model, {}).get("supports_ssml", False)
