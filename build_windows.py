#!/usr/bin/env python3
import os
import sys
import shutil
from datetime import datetime
from pyinstaller_versionfile import create_versionfile
import PyInstaller.__main__

def build():
    # Clean previous builds
    for folder in ('build', 'dist'):
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # Generate version file with date-based build ID
    create_versionfile(
        output_file="version.txt",
        version="0.1.0",  # Hardcoded version - update as needed
        company_name="VoxiomTTS",
        file_description=f"Built: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        internal_name="voxiom-tts",
        legal_copyright="MIT License",
        original_filename="voxiom-tts.exe",
        product_name="Voxiom TTS"
    )

    # PyInstaller build
    PyInstaller.__main__.run([
        'src/main.py',
        '--paths=src', 
        '--onefile',
        '--windowed',
        '--icon=assets/voxiom.ico',
        '--add-data=src/gui/resources.qrc;gui',
        '--add-data=models/silero;models/silero',
        '--version-file=version.txt',
        '--noconfirm',
        '--clean'
    ])

def download_models():
    torch.hub.download_url_to_file(
        'https://models.silero.ai/models/tts/ru/v3_1_ru.pt',
        'models/silero/v3_1_ru.pt'
    )

if __name__ == "__main__":
    build()
