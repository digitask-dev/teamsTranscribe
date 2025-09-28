import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (SRC_ROOT, PROJECT_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from src.config import Settings
from src.transcription import StreamingTranscriber


class _OverlayRecorder:
    def __init__(self) -> None:
        self.texts = []

    def display_text(self, text: str) -> None:
        self.texts.append(text)


def _make_settings(**overrides):
    defaults = dict(
        sample_rate=8,
        chunk_samples=4,
        window_seconds=1.0,
        overlap_seconds=0.0,
        whisper_model_path="base",
        whisper_compute_type="int8",
        whisper_beam_size=1,
        whisper_language=None,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_chunk(values):
    return np.asarray(values, dtype=np.int16).tobytes()


def test_transcriber_emits_after_window():
    overlay = _OverlayRecorder()
    model_calls = []

    class Model:
        def transcribe(self, audio, **kwargs):
            model_calls.append(len(audio))
            return ([SimpleNamespace(text="hello")], None)

    transcriber = StreamingTranscriber(
        settings=_make_settings(),
        overlay=overlay,
        model_factory=lambda: Model(),
    )

    chunk = _make_chunk([1000, 1000, 1000, 1000])
    transcriber.submit(chunk)
    assert overlay.texts == []

    transcriber.submit(chunk)
    assert overlay.texts == ["hello"]
    assert model_calls == [transcriber._window_size]

    transcriber.submit(chunk)
    transcriber.submit(chunk)
    assert overlay.texts == ["hello"]


def test_transcriber_retains_overlap():
    overlay = _OverlayRecorder()

    class Model:
        def transcribe(self, audio, **kwargs):
            return ([SimpleNamespace(text="chunk")], None)

    settings = _make_settings(chunk_samples=8, overlap_seconds=0.5)
    transcriber = StreamingTranscriber(
        settings=settings,
        overlay=overlay,
        model_factory=lambda: Model(),
    )

    values = np.arange(settings.chunk_samples, dtype=np.int16)
    chunk = values.tobytes()
    transcriber.submit(chunk)

    assert overlay.texts == ["chunk"]
    assert transcriber._buffer.size == int(settings.sample_rate * settings.overlap_seconds)
    expected = values[-transcriber._buffer.size :].astype(np.float32) / 32768.0
    np.testing.assert_allclose(transcriber._buffer, expected)


def test_transcriber_disables_vad_when_onnx_missing(capsys):
    overlay = _OverlayRecorder()

    class Model:
        def __init__(self):
            self.calls = 0

        def transcribe(self, audio, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("requires the onnxruntime package")
            return ([SimpleNamespace(text="hi")], None)

    model = Model()
    transcriber = StreamingTranscriber(
        settings=_make_settings(chunk_samples=8),
        overlay=overlay,
        model_factory=lambda: model,
    )

    chunk = _make_chunk([2000] * 8)
    transcriber.submit(chunk)

    captured = capsys.readouterr()
    assert "onnxruntime not available" in captured.out
    assert overlay.texts == ["hi"]
    assert model.calls == 2
    assert transcriber._vad_enabled is False
