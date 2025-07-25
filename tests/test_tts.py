from src.tts.engine import TTSEngine

def test_engine_initialization():
    engine = TTSEngine()
    assert engine.initialize() is True
