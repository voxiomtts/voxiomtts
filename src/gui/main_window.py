from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QTextEdit, 
                              QPushButton, QComboBox, QSlider, QLabel, QMessageBox)
from PySide6.QtCore import Qt, Slot
from src.tts.engine import TTSEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voxiom TTS")
        self.resize(800, 600)
        self.engine = TTSEngine()
        self.init_ui()
        
    def init_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        
        # Text Input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to synthesize...")
        layout.addWidget(self.text_input)
        
        # Voice Selection
        self.voice_box = QComboBox()
        self.voice_box.addItems(["v3_1_ru", "v4_ru"])  # Silero models
        layout.addWidget(self.voice_box)
        
        # Controls
        self.speak_btn = QPushButton("Synthesize")
        self.speak_btn.clicked.connect(self.on_speak)
        layout.addWidget(self.speak_btn)
        
        # Audio Controls
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        layout.addWidget(QLabel("Volume:"))
        layout.addWidget(self.volume_slider)
        
        central_widget.setLayout(layout)
    
    @Slot()
    def on_speak(self):
        text = self.text_input.toPlainText()
        voice = self.voice_box.currentText()
        try:
          self.engine.synthesize(text, voice)
        except Exception as e:
          QMessageBox.critical(self, "Error", f"TTS Failed: {str(e)}")
