import numpy as np
import pyaudio
import threading
from PySide6.QtCore import QObject, Signal

class AudioPlayer(QObject):
    playback_finished = Signal()

    def __init__(self):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self._stop_flag = False

    def play_async(self, audio_numpy, sample_rate=48000):
        """Non-blocking playback with thread"""
        def _play():
            stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=sample_rate,
                output=True
            )
            chunk_size = 1024
            for i in range(0, len(audio_numpy), chunk_size):
                if self._stop_flag:
                    break
                chunk = audio_numpy[i:i+chunk_size].astype(np.float32).tobytes()
                stream.write(chunk)
            stream.stop_stream()
            stream.close()
            self.playback_finished.emit()

        self._stop_flag = False
        threading.Thread(target=_play, daemon=True).start()

    def stop(self):
        self._stop_flag = True
