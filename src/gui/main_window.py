from PySide6.QtWidgets import QMainWindow, QTabWidget
from .synthesis_tab import SynthesisTab
from .settings_tab import SettingsTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoxiomTTS")
        self.resize(800, 600)
        self.init_ui()

    def init_ui(self):
        # Create tabs
        self.tabs = QTabWidget()
        self.synthesis_tab = SynthesisTab()
        self.settings_tab = SettingsTab()
        
        # Add tabs
        self.tabs.addTab(self.synthesis_tab, "Synthesis")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Set central widget
        self.setCentralWidget(self.tabs)
