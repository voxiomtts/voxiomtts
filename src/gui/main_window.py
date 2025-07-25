from PySide6.QtWidgets import (QMainWindow, QTabWidget, QVBoxLayout, QWidget, 
                              QTextEdit, QPushButton, QComboBox, QSlider, 
                              QLabel, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, Slot
from src.tts.engine import TTSEngine
from src.tts.downloader import ModelDownloader

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = TTSEngine()
        self.downloader = ModelDownloader()
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Voxiom TTS")
        self.resize(1000, 700)

        # Main Tab Widget
        tabs = QTabWidget()
        
        # Synthesis Tab
        synth_tab = QWidget()
        self.init_synth_tab(synth_tab)
        
        # Settings Tab
        settings_tab = QWidget()
        self.init_settings_tab(settings_tab)
        
        tabs.addTab(synth_tab, "Synthesize")
        tabs.addTab(settings_tab, "Settings")
        self.setCentralWidget(tabs)

    def init_synth_tab(self, tab):
        layout = QVBoxLayout()
        
        # Text Input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text here...")
        layout.addWidget(self.text_input)
        
        # Speaker Selection
        self.speaker_box = QComboBox()
        self.speaker_box.addItems(["aidar", "baya", "kseniya", "xenia"])
        layout.addWidget(QLabel("Speaker:"))
        layout.addWidget(self.speaker_box)
        
        # Controls
        self.speak_btn = QPushButton("Synthesize")
        self.stop_btn = QPushButton("Stop")
        layout.addWidget(self.speak_btn)
        layout.addWidget(self.stop_btn)
        
        # Audio Controls
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        layout.addWidget(QLabel("Volume:"))
        layout.addWidget(self.volume_slider)
        
        tab.setLayout(layout)

    def init_settings_tab(self, tab):
        layout = QVBoxLayout()
        
        # Model Selection
        self.model_box = QComboBox()
        self.model_box.addItems(["v3_1_ru", "v4_ru"])
        layout.addWidget(QLabel("TTS Model:"))
        layout.addWidget(self.model_box)
        
        # Model Download
        self.download_btn = QPushButton("Update Model")
        self.progress_bar = QProgressBar()
        layout.addWidget(self.download_btn)
        layout.addWidget(self.progress_bar)
        
        # Audio Device Settings
        self.device_box = QComboBox()
        # TODO: Populate with pyaudio devices
        layout.addWidget(QLabel("Audio Device:"))
        layout.addWidget(self.device_box)
        
        tab.setLayout(layout)

    def connect_signals(self):
        # Synthesis Tab
        self.speak_btn.clicked.connect(self.on_synthesize)
        self.stop_btn.clicked.connect(self.engine.player.stop)
        
        # Settings Tab
        self.download_btn.clicked.connect(self.on_download_model)
        self.downloader.progress_updated.connect(self.progress_bar.setValue)
        self.downloader.download_finished.connect(self.on_download_success)
        self.downloader.download_failed.connect(self.on_download_error)

    @Slot()
    def on_synthesize(self):
        text = self.text_input.toPlainText()
        speaker = self.speaker_box.currentText()
        try:
            audio = self.engine.synthesize(text, speaker)
            self.engine.player.play_async(audio)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Synthesis failed: {str(e)}")

    @Slot()
    def on_download_model(self):
        model = self.model_box.currentText()
        self.progress_bar.setRange(0, 100)
        self.downloader.download_model(model)

    @Slot(str)
    def on_download_success(self, path):
        QMessageBox.information(self, "Success", f"Model downloaded to:\n{path}")
        self.progress_bar.reset()

    @Slot(str)
    def on_download_error(self, error):
        QMessageBox.critical(self, "Download Failed", error)
        self.progress_bar.reset()
