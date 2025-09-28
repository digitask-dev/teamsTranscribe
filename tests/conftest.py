import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _install_pyqt5_stub() -> None:
    # Force remove existing PyQt5 modules to ensure stubs are used
    to_delete = [key for key in sys.modules if key == "PyQt5" or key.startswith("PyQt5.")]
    for key in to_delete:
        del sys.modules[key]

    pyqt5 = types.ModuleType("PyQt5")
    qtcore = types.ModuleType("PyQt5.QtCore")
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")

    class _CursorShape:
        SizeAllCursor = "size_all"

    class _MouseButton:
        LeftButton = 1

    class _Qt:
        FramelessWindowHint = 0x01
        WindowStaysOnTopHint = 0x02
        AlignCenter = 0x04
        PointingHandCursor = "pointing"
        CursorShape = _CursorShape()
        MouseButton = _MouseButton()

    class QPoint:
        def __init__(self, x: int = 0, y: int = 0) -> None:
            self._x = x
            self._y = y

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

        def __sub__(self, other: "QPoint") -> "QPoint":
            return QPoint(self._x - other._x, self._y - other._y)

        def __add__(self, other: "QPoint") -> "QPoint":
            return QPoint(self._x + other._x, self._y + other._y)

        def __repr__(self) -> str:  # pragma: no cover - debugging helper
            return f"QPoint({self._x}, {self._y})"

    class _BoundSignal:
        def __init__(self, slots: list) -> None:
            self._slots = slots

        def connect(self, slot) -> None:
            self._slots.append(slot)

        def emit(self, *args, **kwargs) -> None:
            for slot in list(self._slots):
                slot(*args, **kwargs)

    class pyqtSignal:
        def __init__(self, *args, **kwargs) -> None:
            self._name = None

        def __set_name__(self, owner, name) -> None:
            self._name = f"_{name}_slots"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            slots = instance.__dict__.setdefault(self._name, [])
            return _BoundSignal(slots)

    class QSizePolicy:
        Expanding = "expanding"
        Preferred = "preferred"

        def __init__(self, horizontal=None, vertical=None) -> None:
            self.horizontal = horizontal
            self.vertical = vertical

    class QWidget:
        def __init__(self, parent=None) -> None:
            self.parent = parent
            self.children = []
            self._cursor = None
            self._style = None
            self._pos = QPoint(0, 0)
            self._visible = True
            self._layout = None
            self.window_title = ""
            self.window_flags = 0
            self.size = (0, 0)
            self._drag_pos = None

        def setWindowTitle(self, title):
            self.window_title = title

        def setWindowFlags(self, flags):
            self.window_flags = flags

        def setFixedSize(self, width, height):
            self.size = (width, height)

        def setCursor(self, cursor):
            self._cursor = cursor

        def setStyleSheet(self, style):
            self._style = style

        def setLayout(self, layout):
            self._layout = layout

        def layout(self):
            return self._layout

        def show(self):
            self._visible = True

        def hide(self):
            self._visible = False

        def setVisible(self, value):
            self._visible = bool(value)

        def frameGeometry(self):
            point = self._pos

            class _Geom:
                def topLeft(self):  # pragma: no cover - simple helper
                    return QPoint(point.x(), point.y())

            return _Geom()

        def move(self, point):
            if isinstance(point, QPoint):
                self._pos = point
            else:
                self._pos = QPoint(point[0], point[1])

        def pos(self):
            return self._pos

        def mousePressEvent(self, event):
            if hasattr(event, "button") and event.button() == 1:  # Qt.LeftButton
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            # No super() in stub

        def mouseMoveEvent(self, event):
            if self._drag_pos is not None and hasattr(event, "buttons") and (event.buttons() & 1):
                self.move(event.globalPos() - self._drag_pos)
            # No super() in stub

        def mouseReleaseEvent(self, event):
            if hasattr(event, "button") and event.button() == 1:
                self._drag_pos = None
            # No super() in stub

        def close(self):
            pass

    class QLabel(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._text = ""
            self._word_wrap = False
            self._alignment = None
            self._size_policy = None

        def setText(self, text):
            self._text = text

        def text(self):
            return self._text

        def setWordWrap(self, value):
            self._word_wrap = bool(value)

        def setAlignment(self, alignment):
            self._alignment = alignment

        def setSizePolicy(self, horizontal, vertical):
            self._size_policy = (horizontal, vertical)

    class QPushButton(QWidget):
        clicked = pyqtSignal()

        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = text

        def setFixedSize(self, width, height):
            self.size = (width, height)

        def setStyleSheet(self, style):
            self._style = style

        def setCursor(self, cursor):
            self._cursor = cursor

        def setText(self, text):
            self._text = text

        def text(self):
            return self._text

        def click(self):
            slots = self.__dict__.get("_clicked_slots", [])
            for slot in list(slots):
                slot()

    class QLayout:
        def __init__(self, parent=None):
            self.parent = parent
            self._margins = (0, 0, 0, 0)
            self._spacing = 0
            self._items = []

        def setContentsMargins(self, left, top, right, bottom):
            self._margins = (left, top, right, bottom)

        def setSpacing(self, spacing):
            self._spacing = spacing

        def addWidget(self, widget, stretch=0):
            self._items.append(("widget", widget, stretch))

        def addLayout(self, layout, stretch=0):
            self._items.append(("layout", layout, stretch))

    class QHBoxLayout(QLayout):
        pass

    class QVBoxLayout(QLayout):
        pass

    class QApplication:
        def __init__(self, args=None):
            self.args = args or []

        def exec_(self):
            return 0

    setattr(qtcore, "Qt", _Qt())
    setattr(qtcore, "QPoint", QPoint)
    setattr(qtcore, "pyqtSignal", pyqtSignal)

    setattr(qtwidgets, "QWidget", QWidget)
    setattr(qtwidgets, "QLabel", QLabel)
    setattr(qtwidgets, "QPushButton", QPushButton)
    setattr(qtwidgets, "QHBoxLayout", QHBoxLayout)
    setattr(qtwidgets, "QVBoxLayout", QVBoxLayout)
    setattr(qtwidgets, "QApplication", QApplication)
    setattr(qtwidgets, "QSizePolicy", QSizePolicy)

    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtCore"] = qtcore
    sys.modules["PyQt5.QtWidgets"] = qtwidgets


class _Stream:
    def __init__(self, frames=None):
        self.frames = list(frames or [])
        self._index = 0
        self.stopped = False
        self.closed = False

    def read(self, chunk_samples, exception_on_overflow=False):
        if self._index < len(self.frames):
            frame = self.frames[self._index]
            self._index += 1
            return frame
        # default to silence
        return b"\x00\x00" * chunk_samples

    def stop_stream(self):
        self.stopped = True

    def close(self):
        self.closed = True


class _PyAudio:
    devices = []
    host_apis = {}
    open_callback = None

    def __init__(self):
        pass

    def get_device_count(self):
        return len(self.devices)

    def get_device_info_by_index(self, index):
        return self.devices[index]

    def get_host_api_info_by_index(self, index):
        return self.host_apis.get(index, {})

    def open(self, **kwargs):
        if callable(self.open_callback):
            return self.open_callback(**kwargs)
        return _Stream()

    def terminate(self):
        pass


class _PyAudioModule(types.ModuleType):
    def __init__(self):
        super().__init__("pyaudio")
        self.PyAudio = _PyAudio
        self.Stream = _Stream
        self.paInt16 = 8


class _FasterWhisperModel:
    _callback = None

    def __init__(self, model_path, device="auto", compute_type="int8"):
        self.model_path = model_path
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio, **kwargs):
        if callable(self.__class__._callback):
            return self.__class__._callback(audio, **kwargs)
        segment = types.SimpleNamespace(text="")
        return ([segment], None)

    @classmethod
    def set_transcribe_callback(cls, callback):
        cls._callback = callback


class _FasterWhisperModule(types.ModuleType):
    def __init__(self):
        super().__init__("faster_whisper")
        self.WhisperModel = _FasterWhisperModel


def _install_pyaudio_stub() -> None:
    # Force remove existing pyaudio module
    if "pyaudio" in sys.modules:
        del sys.modules["pyaudio"]

    sys.modules["pyaudio"] = _PyAudioModule()


def _install_faster_whisper_stub() -> None:
    # Force remove existing faster_whisper module
    if "faster_whisper" in sys.modules:
        del sys.modules["faster_whisper"]

    sys.modules["faster_whisper"] = _FasterWhisperModule()


_install_pyqt5_stub()
_install_pyaudio_stub()
_install_faster_whisper_stub()


import pytest


@pytest.fixture(autouse=True)
def _reset_stubs():
    import pyaudio
    from faster_whisper import WhisperModel

    pyaudio.PyAudio.devices = []  # type: ignore[attr-defined]
    pyaudio.PyAudio.host_apis = {}  # type: ignore[attr-defined]
    pyaudio.PyAudio.open_callback = None  # type: ignore[attr-defined]
    if hasattr(WhisperModel, "set_transcribe_callback"):
        WhisperModel.set_transcribe_callback(None)  # type: ignore[attr-defined]
    yield
    pyaudio.PyAudio.devices = []  # type: ignore[attr-defined]
    pyaudio.PyAudio.host_apis = {}  # type: ignore[attr-defined]
    pyaudio.PyAudio.open_callback = None  # type: ignore[attr-defined]
    if hasattr(WhisperModel, "set_transcribe_callback"):
        WhisperModel.set_transcribe_callback(None)  # type: ignore[attr-defined]


