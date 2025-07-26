import sys
import os
from gui.main_window import MainWindow  # Now using relative import
from PySide6.QtWidgets import QApplication

# Fix Python 3.9 path resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
