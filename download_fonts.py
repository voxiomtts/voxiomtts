# -*- coding: utf-8 -*-
import os
import subprocess
from pathlib import Path

def download_noto_emoji():
    """Download Noto Color Emoji font with curl"""
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    font_path = assets_dir / "NotoColorEmoji.ttf"

    if not font_path.exists():
        print("Downloading Noto Color Emoji...")
        try:
            # Cross-platform curl implementation
            if os.name == 'nt':  # Windows
                subprocess.run([
                    "curl", "-L",
                    "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf",
                    "-o", str(font_path)
                ], check=True)
            else:  # Linux/Mac
                subprocess.run([
                    "curl", "-fLo", str(font_path),
                    "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf"
                ], check=True)
            print("Download successful!")
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    return True

if __name__ == "__main__":
    download_noto_emoji()
