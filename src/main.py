import os
import sys
import threading
from typing import List, Tuple, Optional, Any

import numpy as np
import pyaudio
from faster_whisper import WhisperModel
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 4096

# Smaller window sizes update the overlay faster but reduce Whisper context.
def _parse_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


WINDOW_SECONDS = max(
    _parse_float(os.environ.get("WHISPER_WINDOW_SECONDS"), 1.5),
    0.5,
)
OVERLAP_SECONDS = max(
    _parse_float(os.environ.get("WHISPER_OVERLAP_SECONDS"), 0.4),
    0.0,
)

WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", "base")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "1"))

language_override = os.environ.get("WHISPER_LANGUAGE", "auto")
WHISPER_LANGUAGE = None if language_override.lower() == "auto" else language_override

_WHISPER_MODEL: Optional[WhisperModel] = None


def get_whisper_model() -> WhisperModel:
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        print(
            f"Loading faster-whisper model '{WHISPER_MODEL_PATH}' "
            f"(compute_type={WHISPER_COMPUTE_TYPE})"
        )
        _WHISPER_MODEL = WhisperModel(
            WHISPER_MODEL_PATH,
            device="auto",
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _WHISPER_MODEL


class OverlayWindow(QLabel):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Live Transcription")
        self.setStyleSheet(
            "font-size: 20px; color: white; background-color: rgba(0, 0, 0, 150);"
        )
        self.setAlignment(Qt.AlignCenter)  # type: ignore
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # type: ignore
        self.resize(800, 200)
        self.show()

    def update_text(self, text: str) -> None:
        if text.strip():
            self.setText(text)


class StreamingTranscriber:
    def __init__(self, overlay: OverlayWindow, model: WhisperModel) -> None:
        self.overlay = overlay
        self.model = model
        self.window_size = int(SAMPLE_RATE * WINDOW_SECONDS)
        self.overlap_size = int(SAMPLE_RATE * OVERLAP_SECONDS)
        self.buffer = np.zeros(0, dtype=np.float32)
        self.last_text = ""

    def submit(self, chunk: bytes) -> None:
        if not chunk:
            return

        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        if not samples.size:
            return

        self.buffer = np.concatenate((self.buffer, samples))
        if self.buffer.size < self.window_size:
            return

        audio = self.buffer.copy()
        try:
            segments, _ = self.model.transcribe(
                audio,
                beam_size=WHISPER_BEAM_SIZE,
                temperature=0.0,
                vad_filter=True,
                language=WHISPER_LANGUAGE,
            )
            text = "".join(segment.text for segment in segments).strip()
        except Exception as exc:
            print(f"Transcription error: {exc}")
            text = ""

        if text and text != self.last_text:
            self.overlay.update_text(text)
            self.last_text = text

        if self.overlap_size and self.overlap_size < self.buffer.size:
            self.buffer = self.buffer[-self.overlap_size :]
        else:
            self.buffer = np.zeros(0, dtype=np.float32)


def find_loopback_devices(p: pyaudio.PyAudio) -> List[Tuple[int, Any]]:
    devices: List[Tuple[int, Any]] = []
    for idx in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(idx)
        name = str(dev_info.get("name", "")).lower()
        host_api_name = ""
        host_api_index = dev_info.get("hostApi")
        if host_api_index is not None:
            try:
                host_api_name = p.get_host_api_info_by_index(int(host_api_index)).get(
                    "name", ""
                )
            except Exception:
                host_api_name = ""

        if (
            "loopback" in name
            or "vb-audio" in name
            or "virtual" in name
            or "cable" in name
            or "wasapi" in str(host_api_name).lower()
        ):
            devices.append((idx, dev_info))
    return devices


def open_input_stream(p: pyaudio.PyAudio, device_index: Optional[int] = None):
    return p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SAMPLES,
        input_device_index=device_index,
    )


def transcribe_audio(overlay: OverlayWindow, use_system_audio: bool = False) -> None:
    model = get_whisper_model()
    transcriber = StreamingTranscriber(overlay, model)

    p = pyaudio.PyAudio()
    stream = None

    try:
        if use_system_audio:
            loopback_devices = find_loopback_devices(p)
            if loopback_devices:
                device_index = loopback_devices[0][0]
                print(f"Using system audio device: {loopback_devices[0][1]['name']}")
                stream = open_input_stream(p, device_index=device_index)
            else:
                print("No loopback device found. Falling back to microphone.")

        if stream is None:
            stream = open_input_stream(p)

        print("Listening for speech...")
        while True:
            data = stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
            transcriber.submit(data)
    except KeyboardInterrupt:
        print("Stopping transcription...")
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        p.terminate()


def transcribe_both_audio(overlay: OverlayWindow) -> None:
    model = get_whisper_model()
    transcriber = StreamingTranscriber(overlay, model)

    p = pyaudio.PyAudio()
    mic_stream = None
    system_stream = None

    try:
        mic_stream = open_input_stream(p)

        loopback_devices = find_loopback_devices(p)
        if loopback_devices:
            device_index = loopback_devices[0][0]
            print(f"Using system audio device: {loopback_devices[0][1]['name']}")
            system_stream = open_input_stream(p, device_index=device_index)
        else:
            print("No loopback device found. Using microphone only.")

        print("Listening for speech from both microphone and system audio...")

        while True:
            mic_data = mic_stream.read(CHUNK_SAMPLES, exception_on_overflow=False)

            if system_stream:
                try:
                    system_data = system_stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
                except IOError:
                    system_data = mic_data
            else:
                system_data = mic_data

            mixed_data = mix_audio(mic_data, system_data)
            transcriber.submit(mixed_data)
    except KeyboardInterrupt:
        print("Stopping transcription...")
    finally:
        if mic_stream is not None:
            mic_stream.stop_stream()
            mic_stream.close()
        if system_stream is not None:
            system_stream.stop_stream()
            system_stream.close()
        p.terminate()


def mix_audio(data1: bytes, data2: bytes) -> bytes:
    arr1 = np.frombuffer(data1, dtype=np.int16)
    arr2 = np.frombuffer(data2, dtype=np.int16)

    min_len = min(len(arr1), len(arr2))
    if min_len == 0:
        return data1 if len(arr1) >= len(arr2) else data2

    arr1 = arr1[:min_len]
    arr2 = arr2[:min_len]

    mixed = ((arr1.astype(np.int32) + arr2.astype(np.int32)) / 2).astype(np.int16)
    return mixed.tobytes()


def list_audio_devices() -> None:
    p = pyaudio.PyAudio()
    print("\nAvailable audio devices:")
    print("-" * 50)
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        host_api_name = ""
        host_api_index = dev_info.get("hostApi")
        if host_api_index is not None:
            try:
                host_api_name = p.get_host_api_info_by_index(int(host_api_index)).get(
                    "name", ""
                )
            except Exception:
                host_api_name = str(host_api_index)
        print(f"Device {i}: {dev_info['name']}")
        print(f"  Host API: {host_api_name}")
        print(f"  Max Input Channels: {dev_info['maxInputChannels']}")
        print(f"  Max Output Channels: {dev_info['maxOutputChannels']}")
        print()
    p.terminate()


# list_audio_devices()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Live audio transcription")
    parser.add_argument(
        "--mic-only",
        action="store_true",
        help="Capture microphone audio only",
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        help="Capture system audio output only",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    overlay = OverlayWindow()

    if args.mic_only:
        thread = threading.Thread(
            target=transcribe_audio,
            args=(overlay, False),
            daemon=True,
        )
    elif args.system_only:
        thread = threading.Thread(
            target=transcribe_audio,
            args=(overlay, True),
            daemon=True,
        )
    else:
        thread = threading.Thread(
            target=transcribe_both_audio,
            args=(overlay,),
            daemon=True,
        )

    thread.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
