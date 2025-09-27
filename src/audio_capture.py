from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Iterator, List, Optional, Tuple

import numpy as np
import pyaudio

from config import Settings


LoopbackDevice = Tuple[int, Any]


def find_loopback_devices(p: pyaudio.PyAudio) -> List[LoopbackDevice]:
    devices: List[LoopbackDevice] = []
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


@contextmanager
def managed_input_stream(
    p: pyaudio.PyAudio,
    settings: Settings,
    device_index: Optional[int] = None,
) -> Generator[pyaudio.Stream, None, None]:
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=settings.sample_rate,
        input=True,
        frames_per_buffer=settings.chunk_samples,
        input_device_index=device_index,
    )
    try:
        yield stream
    finally:
        stream.stop_stream()
        stream.close()


def stream_frames(stream: pyaudio.Stream, chunk_samples: int) -> Iterator[bytes]:
    while True:
        yield stream.read(chunk_samples, exception_on_overflow=False)


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
