#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from pyinstaller_versionfile import create_versionfile
import PyInstaller.__main__

# Import version info
sys.path.insert(0, os.path.abspath('.'))
try:
    from src import version
except ImportError:
    import version

def generate_version_file():
    """Generate version resource with auto-increment build number"""
    build_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    version_str = f"{version.__version__}.{getattr(version, '__build_num__', 0)}"
    
    create_versionfile(
        output_file="version.txt",
        version=version_str,
        company_name="VoxiomTTS",
        file_description="Text-to-Speech Application|Голосовой синтезатор",
        internal_name="voxiom-tts",
        legal_copyright="MIT License|Лицензия MIT",
        original_filename="voxiom-tts.exe",
        product_name="Voxiom TTS|Voxiom TTS (Рус)",
        private_build=build_date,
        translations=[
            {"lang": 1033, "charset": 1252},  # English
            {"lang": 1049, "charset": 1251}    # Russian
        ]
    )

def build():
    # Clean previous builds
    for folder in ('build', 'dist'):
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # Generate fresh version file
    generate_version_file()

    # PyInstaller configuration
    PyInstaller.__main__.run([
        'src/main.py',
        '--onefile',
        '--windowed',
        '--icon=assets/voxiom.ico',
        '--add-data=src/gui/resources.qrc;gui',
        '--add-data=models/silero;models/silero',
        '--version-file=version.txt',
        '--noconfirm',
        '--clean',
        '--paths=src'
    ])

if __name__ == "__main__":
    build()
