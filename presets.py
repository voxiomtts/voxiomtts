import json
from pathlib import Path
from typing import Dict, Any

def load_presets(file_path: str = "presets.json") -> Dict[str, Any]:
    """Load presets from JSON file with error handling"""
    try:
        with open(Path(__file__).parent / file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load presets: {e}")
        return {
            "Error": {
                "default": "Presets failed to load. Please check presets.json"
            }
        }
