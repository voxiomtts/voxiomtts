#!/usr/bin/env python3
import os
import sys
import shutil
from pyinstaller_versionfile import create_versionfile
import PyInstaller.__main__

# Import version info
sys.path.insert(0, os.path.abspath('.'))
from src import version  # Requires __version__ in version.py

def build():
    # Clean previous builds
    for folder in ('build', 'dist'):
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # Generate version file
    create_versionfile(
        output_file="version.txt",
        version=version.__version__,
        company_name="VoxiomTTS",
        file_description=f"Build: {datetime.now().strftime('%Y-%m-%d')}",  # Date as build identifier
        internal_name="voxiom-tts",
        legal_copyright="MIT License",
        original_filename="voxiom-tts.exe",
        product_name="Voxiom TTS"
    )

    # PyInstaller build
    PyInstaller.__main__.run([
        'src/main.py',
        '--onefile',
        '--windowed',
        '--icon=assets/voxiom.ico',
        '--add-data=src/gui/resources.qrc;gui',
        '--add-data=models/silero;models/silero',
        '--version-file=version.txt',
        '--noconfirm',
        '--clean'
    ])

if __name__ == "__main__":
    build()
