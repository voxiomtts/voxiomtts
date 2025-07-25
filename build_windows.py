import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import PyInstaller.__main__
# In build_windows.py
try:
    import version  # Try relative import
except ImportError:
    from src import version  # Fallback to absolute
from pathlib import Path

def build():
    # Create versioned output dir
    build_dir = Path(f"build/v{version.__version__}")
    build_dir.mkdir(parents=True, exist_ok=True)

    PyInstaller.__main__.run([
        'src/main.py',
        f'--distpath={build_dir}',  # Version-specific output
        '--name=VoxiomTTS',
        '--onefile',
        '--windowed',
        '--icon=assets/voxiom.ico',
        '--add-data=src/gui/resources.qrc;gui',
        '--add-data=models/silero;models/silero',
        '--version-file=version.rc',
        '--win-private-assemblies',
        '--noconfirm',
        '--clean'
    ])

if __name__ == "__main__":
    build()
