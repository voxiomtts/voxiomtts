name: Create Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build executable
        run: |
          pip install pyinstaller
          pyinstaller --onefile --windowed \
                      --icon=assets/voxiom.ico \
                      --name Voxiom_TTS \
                      --add-data "assets/voxiom.ico;assets" \
                      main.py
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: Voxiom-TTS-GUI
          path: dist/
