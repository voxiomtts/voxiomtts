from PySide6.QtWidgets import QMainWindow, QLabel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoxiomTTS")
        self.setMinimumSize(400, 300)
        
        # Temporary label
        self.label = QLabel("TTS Application Initialized", self)
        self.label.move(50, 50)
