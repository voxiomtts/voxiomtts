from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                              QPushButton, QProgressBar, QLabel, QTextEdit)

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["v3_ru", "v4_ru"])
        model_layout.addWidget(self.model_combo)
        self.update_btn = QPushButton("Update Model")
        model_layout.addWidget(self.update_btn)
        
        # Update progress
        self.update_progress = QProgressBar()
        
        # Credits
        self.credits = QTextEdit()
        self.credits.setReadOnly(True)
        self.credits.setText("VoxiomTTS\n\nUsing Silero TTS models\n\nDeveloped by YourName")
        
        # Add to main layout
        layout.addLayout(model_layout)
        layout.addWidget(self.update_progress)
        layout.addWidget(QLabel("Credits:"))
        layout.addWidget(self.credits)
        
        self.setLayout(layout)
