import numpy as np

import pyaudio

from src.config import Settings
from src.audio_capture import (
    list_audio_devices,
    stream_frames,
    managed_input_stream,
    mix_audio,
    find_loopback_devices,
)


class MockStream(pyaudio.Stream):
    def __init__(self, frames):
        self.frames = list(frames)
        self._index = 0
        self.stopped = False
        self.closed = False

    def read(self, chunk_samples, exception_on_overflow=False):
        if self._index < len(self.frames):
            frame = self.frames[self._index]
            self._index += 1
            return frame
        # Simulate silence for int16 mono (2 bytes per sample)
        return b"\x00" * (chunk_samples * 2)

    def stop_stream(self):
        self.stopped = True

    def close(self):
        self.closed = True


def _settings():
    return Settings(
        sample_rate=16000,
        chunk_samples=4,
        window_seconds=1.0,
        overlap_seconds=0.0,
        whisper_model_path="base",
        whisper_compute_type="int8",
        whisper_beam_size=1,
        whisper_language=None,
    )

def test_managed_input_stream_closes_stream(monkeypatch):
    stream = MockStream([b"abcd"])
    monkeypatch.setattr(pyaudio.PyAudio, 'open', lambda self, **kwargs: stream)

    p = pyaudio.PyAudio()
    with managed_input_stream(p, _settings()):
        pass

    assert stream.stopped is True
    assert stream.closed is True

def test_mix_audio_returns_longer_when_other_empty():
    a = np.array([1, 2, 3, 4], dtype=np.int16).tobytes()
    b = np.array([], dtype=np.int16).tobytes()

    mixed = mix_audio(a, b)
    assert mixed == a

    mixed2 = mix_audio(b, a)
    assert mixed2 == a

def test_list_audio_devices_prints(capsys, monkeypatch):
    monkeypatch.setattr(pyaudio.PyAudio, "devices", [
        {"name": "Device A", "hostApi": 0, "maxInputChannels": 2, "maxOutputChannels": 0},
    ])
    monkeypatch.setattr(pyaudio.PyAudio, "host_apis", {0: {"name": "DirectSound"}})

    list_audio_devices()
    captured = capsys.readouterr()
    assert "Device 0: Device A" in captured.out
    assert "DirectSound" in captured.out
    list_audio_devices()
    captured = capsys.readouterr()
    
def test_stream_frames_yields_from_stream(monkeypatch):
    stream = MockStream([b"abcd", b"wxyz"])
    frames = stream_frames(stream, chunk_samples=4)
    assert next(frames) == b"abcd"
    assert next(frames) == b"wxyz"
