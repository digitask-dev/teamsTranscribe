from __future__ import annotations

from contextlib import ExitStack
from typing import Callable, Optional

import numpy as np
import pyaudio
from faster_whisper import WhisperModel

from config import Settings
from model_loader import get_model
from overlay import OverlayWindow
from audio_capture import managed_input_stream, find_loopback_devices, mix_audio


class StreamingTranscriber:
    def __init__(
        self,
        settings: Settings,
        overlay: OverlayWindow,
        model_factory: Optional[Callable[[], WhisperModel]] = None,
    ) -> None:
        self.settings = settings
        self.overlay = overlay
        self._buffer = np.zeros(0, dtype=np.float32)
        self._last_text = ""
        self._window_size = max(1, int(settings.sample_rate * settings.window_seconds))
        self._overlap_size = max(0, int(settings.sample_rate * settings.overlap_seconds))
        self._model_factory = model_factory or (lambda: get_model(settings))
        self._model: Optional[WhisperModel] = None
        self._vad_enabled = True

    def submit(self, chunk: bytes) -> None:
        if not chunk:
            return

        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        if not samples.size:
            return

        self._buffer = np.concatenate((self._buffer, samples))
        if self._buffer.size < self._window_size:
            return

        audio = self._buffer.copy()
        text = self._transcribe_audio(audio)

        if text and text != self._last_text:
            self.overlay.display_text(text)
            self._last_text = text

        if self._overlap_size and self._overlap_size < self._buffer.size:
            self._buffer = self._buffer[-self._overlap_size :]
        else:
            self._buffer = np.zeros(0, dtype=np.float32)

    def _transcribe_audio(self, audio: np.ndarray) -> str:
        attempts = 2 if self._vad_enabled else 1
        for attempt in range(attempts):
            try:
                model = self._get_model()
                segments, _ = model.transcribe(
                    audio,
                    beam_size=self.settings.whisper_beam_size,
                    temperature=0.0,
                    vad_filter=self._vad_enabled,
                    language=self.settings.whisper_language,
                )
                return "".join(segment.text for segment in segments).strip()
            except Exception as exc:
                message = str(exc).lower()
                missing_vad_dep = "requires the onnxruntime package" in message
                if self._vad_enabled and missing_vad_dep:
                    print("onnxruntime not available; disabling VAD filter for this session.")
                    self._vad_enabled = False
                    continue
                print(f"Transcription error: {exc}")
                break
        return ""

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = self._model_factory()
        return self._model


def _consume_stream(stream, settings: Settings, transcriber: StreamingTranscriber) -> None:
    while True:
        chunk = stream.read(settings.chunk_samples, exception_on_overflow=False)
        transcriber.submit(chunk)


def transcribe_audio(
    overlay: OverlayWindow,
    settings: Settings,
    use_system_audio: bool = False,
) -> None:
    transcriber = StreamingTranscriber(settings, overlay)
    p = pyaudio.PyAudio()

    try:
        device_index: Optional[int] = None
        device_name: Optional[str] = None

        if use_system_audio:
            loopback_devices = find_loopback_devices(p)
            if loopback_devices:
                device_index, info = loopback_devices[0]
                device_name = info.get("name")
                print(f"Using system audio device: {device_name}")
            else:
                print("No loopback device found. Falling back to microphone.")

        with managed_input_stream(p, settings, device_index) as stream:
            if device_name:
                print("Listening for system audio...")
            else:
                print("Listening for speech...")
            _consume_stream(stream, settings, transcriber)
    except KeyboardInterrupt:
        print("Stopping transcription...")
    finally:
        p.terminate()


def transcribe_both_audio(overlay: OverlayWindow, settings: Settings) -> None:
    transcriber = StreamingTranscriber(settings, overlay)
    p = pyaudio.PyAudio()

    try:
        with ExitStack() as stack:
            mic_stream = stack.enter_context(managed_input_stream(p, settings))

            loopback_devices = find_loopback_devices(p)
            system_stream = None
            if loopback_devices:
                device_index, info = loopback_devices[0]
                print(f"Using system audio device: {info.get('name')}")
                system_stream = stack.enter_context(
                    managed_input_stream(p, settings, device_index)
                )
            else:
                print("No loopback device found. Using microphone only.")

            print("Listening for speech from both microphone and system audio...")

            while True:
                mic_data = mic_stream.read(
                    settings.chunk_samples, exception_on_overflow=False
                )

                if system_stream is not None:
                    try:
                        system_data = system_stream.read(
                            settings.chunk_samples, exception_on_overflow=False
                        )
                    except IOError:
                        system_data = mic_data
                else:
                    system_data = mic_data

                mixed_data = mix_audio(mic_data, system_data)
                transcriber.submit(mixed_data)
    except KeyboardInterrupt:
        print("Stopping transcription...")
    finally:
        p.terminate()
