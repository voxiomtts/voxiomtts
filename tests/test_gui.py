import pytest
from src.gui.main_window import MainWindow

def test_window_creation(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "VoxiomTTS"
