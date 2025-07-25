MODELS = {
    "silero": {
        "v3": "models/silero/v3_1_ru.pt",
        "v4": "models/silero/v4_ru.pt"
    }
}

def validate_model(path: str) -> bool:
    """Check if model file exists"""
    import os
    return os.path.exists(path)
