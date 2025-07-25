import pyaudio
import wave
import numpy as np

class AudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        
    def play(self, audio_numpy, sample_rate=48000):
        stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=sample_rate,
            output=True
        )
        stream.write(audio_numpy.astype(np.float32).tobytes())
        stream.stop_stream()
        stream.close()
