import os
import sys
from pathlib import Path
import PyInstaller.__main__

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import version with fallback
try:
    from src import version  # First try absolute import
except ImportError:
    import version  # Fallback to relative (only for development)

def build():
    # Create versioned output dir
    build_dir = Path(f"build/v{version.__version__}")
    build_dir.mkdir(parents=True, exist_ok=True)

    # PyInstaller configuration
    pyi_args = [
        'src/main.py',
        f'--distpath={build_dir}',
        '--name=VoxiomTTS',
        '--onefile',
        '--windowed',
        '--icon=assets/voxiom.ico',
        '--add-data=src/gui/resources.qrc;gui',
        '--add-data=models/silero;models/silero',
        '--version-file=version.rc',
        '--win-private-assemblies',
        '--noconfirm',
        '--clean',
        '--paths=src'  # Explicitly tell PyInstaller where to look for modules
    ]

    # Add hidden imports if needed
    if 'src.version' not in sys.modules:
        pyi_args.append('--hidden-import=src.version')

    PyInstaller.__main__.run(pyi_args)

if __name__ == "__main__":
    build()
