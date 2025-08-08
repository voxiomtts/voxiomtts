# -*- coding: utf-8 -*-
import os
import hashlib
import requests
import torch
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional

MODELS = {
    "v3_en": {
        "url": "https://models.silero.ai/models/tts/en/v3_en.pt",
        "file": "v3_en.pt",
        "sha256": "02B71034D9F13BC4001195017BAC9DB1C6BB6115E03FEA52983E8ABCFF13B665",
        "language": "English"
    },
    "v3_1_ru": {
        "url": "https://models.silero.ai/models/tts/ru/v3_1_ru.pt",
        "file": "v3_1_ru.pt",
        "sha256": "CF60B47EC8A9C31046021D2D14B962EA56B8A5BF7061C98ACCAAACA428522F85",
        "language": "Russian"
    },
    "v4_ru": {
        "url": "https://models.silero.ai/models/tts/ru/v4_ru.pt",
        "file": "v4_ru.pt",
        "sha256": "896AB96347D5BD781AB97959D4FD6885620E5AAB52405D3445626EB7C1414B00",
        "language": "Russian (SSML)",
        "supports_ssml": True
    }
}

class ModelUpdater:
    def __init__(self, models_dir: str = "models/tts"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _download_with_progress(self, url: str, destination: Path) -> bool:
        """Download with progress bar and hash verification"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            with open(destination, 'wb') as f, tqdm(
                desc=f"Downloading {destination.name}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            if destination.exists():
                destination.unlink()
            return False

    def check_model(self, model_name: str) -> Dict[str, str]:
        """Check model status with detailed info"""
        model_info = MODELS[model_name]
        model_path = self.models_dir / model_info["file"]

        status = {
            "name": model_name,
            "installed": False,
            "valid": False,
            "path": str(model_path),
            "language": model_info.get("language", "Unknown"),
            "features": []
        }

        if model_path.exists():
            status["installed"] = True
            if self._calculate_sha256(model_path) == model_info["sha256"]:
                status["valid"] = True
                status["features"].append("Verified")

            # Additional validation by trying to load
            try:
                torch.jit.load(model_path, map_location='cpu')
                status["features"].append("Loadable")
            except Exception:
                status["features"].append("Corrupted")

        if model_info.get("supports_ssml"):
            status["features"].append("SSML")

        return status

    def update_models(self, selected_models: List[str], force: bool = False) -> Dict[str, str]:
        """Update selected models with verification"""
        results = {}

        for model_name in selected_models:
            if model_name not in MODELS:
                results[model_name] = "Error: Unknown model"
                continue

            model_info = MODELS[model_name]
            model_path = self.models_dir / model_info["file"]

            # Skip if already valid and not forced
            if not force and model_path.exists():
                if self._calculate_sha256(model_path) == model_info["sha256"]:
                    results[model_name] = "Already up-to-date"
                    continue

            # Download and verify
            if self._download_with_progress(model_info["url"], model_path):
                if self._calculate_sha256(model_path) == model_info["sha256"]:
                    results[model_name] = "Successfully updated"
                else:
                    results[model_name] = "Error: Hash mismatch"
                    model_path.unlink()
            else:
                results[model_name] = "Error: Download failed"

        return results

# GUI Integration Example (to be called from your Settings Tab)
def get_available_models() -> List[Dict]:
    return [
        {
            "name": name,
            "language": info["language"],
            "supports_ssml": info.get("supports_ssml", False),
            "selected": False  # Default checkbox state
        }
        for name, info in MODELS.items()
    ]
