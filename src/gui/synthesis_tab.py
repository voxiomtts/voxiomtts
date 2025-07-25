from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                              QComboBox, QPushButton, QProgressBar, QSlider, 
                              QLabel, QFileDialog)
from PySide6.QtCore import Qt, Signal, QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class SynthesisTab(QWidget):
    play_clicked = Signal()
    stop_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_audio_meter()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Text input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to synthesize...")
        
        # Controls
        control_layout = QHBoxLayout()
        self.speaker_combo = QComboBox()
        self.speaker_combo.addItems(["aidar", "baya", "kseniya", "xenia"])
        
        self.generate_btn = QPushButton("Generate")
        self.play_btn = QPushButton("Play")
        self.stop_btn = QPushButton("Stop")
        self.save_btn = QPushButton("Save WAV")
        
        # Progress
        self.progress = QProgressBar()
        
        # Add to layout
        control_layout.addWidget(QLabel("Speaker:"))
        control_layout.addWidget(self.speaker_combo)
        control_layout.addWidget(self.generate_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.save_btn)
        
        # Waveform visualization
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Audio level meter
        self.audio_level = QSlider(Qt.Horizontal)
        self.audio_level.setRange(0, 100)
        self.audio_level.setEnabled(False)
        
        # Assemble main layout
        main_layout.addWidget(self.text_input)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(QLabel("Audio Level:"))
        main_layout.addWidget(self.audio_level)
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.play_btn.clicked.connect(self.play_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.save_btn.clicked.connect(self.save_audio)

    def setup_audio_meter(self):
        self.meter_timer = QTimer()
        self.meter_timer.timeout.connect(self.update_audio_meter)
        self.meter_timer.start(100)  # Update every 100ms

    def update_audio_meter(self):
        # This will be connected to engine's audio level
        pass

    def save_audio(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save WAV File", "", "WAV Files (*.wav)")
        if filename:
            self.save_requested.emit(filename)

    def plot_waveform(self, audio_data):
        self.ax.clear()
        self.ax.plot(audio_data)
        self.canvas.draw()
