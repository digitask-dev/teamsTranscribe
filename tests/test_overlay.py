from PyQt5.QtCore import QPoint, Qt

from src.overlay import OverlayWindow


def test_overlay_initial_state():
    overlay = OverlayWindow(width=600, height=120)

    assert overlay.window_title == "Live Transcription"
    assert overlay.window_flags == (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint) # type: ignore
    assert overlay.size == (600, 120)

    assert overlay.info_label._visible is False
    assert overlay.toggle_button.text() == "\u25BE"


def test_overlay_toggle_visibility():
    overlay = OverlayWindow()

    assert overlay.info_label._visible is False
    assert overlay.toggle_button.text() == "\u25BE"

    overlay.toggle_button.click()
    assert overlay.info_label._visible is True
    assert overlay.toggle_button.text() == "\u25B4"

    overlay.toggle_button.click()
    assert overlay.info_label._visible is False
    assert overlay.toggle_button.text() == "\u25BE"


def test_overlay_status_and_drag():
    overlay = OverlayWindow()

    overlay.set_status_info(model="base", language=None, compute_type="int8")
    assert "Model: base" in overlay.info_label.text()
    assert "Language: Auto" in overlay.info_label.text()

    class _Event:
        def __init__(self, global_pos):
            self._global = global_pos
            self._accepted = False

        def button(self):
            return Qt.MouseButton.LeftButton

        def buttons(self):
            return Qt.MouseButton.LeftButton

        def globalPos(self):
            return self._global

        def accept(self):
            self._accepted = True

    press_event = _Event(QPoint(10, 15))
    move_event = _Event(QPoint(30, 40))
    release_event = _Event(QPoint(30, 40))

    overlay.mousePressEvent(press_event)
    overlay.mouseMoveEvent(move_event)
    overlay.mouseReleaseEvent(release_event)

    pos = overlay.pos()
    assert pos.x() == 20
    assert pos.y() == 25
