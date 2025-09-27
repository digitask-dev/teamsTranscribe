from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QPushButton, QSizePolicy


class OverlayWindow(QWidget):
    text_requested = pyqtSignal(str)

    def __init__(self, width: int = 800, height: int = 90) -> None:
        super().__init__()

        self.setWindowTitle("Live Transcription")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # type: ignore
        self.setFixedSize(width, height)
        self.setStyleSheet(
            "background-color: rgba(0, 0, 0, 150); border-radius: 6px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 12, 8)
        layout.setSpacing(8)

        self.label = QLabel(self)
        self.label.setStyleSheet("font-size: 20px; color: white;")
        self.label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(self.label, 1)

        self.close_button = QPushButton("X", self)
        self.close_button.setFixedSize(24, 24)
        self.close_button.setStyleSheet(
            "color: white; background-color: rgba(255, 255, 255, 60);"
            "border: none; font-size: 14px;"
        )
        self.close_button.setCursor(Qt.PointingHandCursor)  # type: ignore
        self.close_button.clicked.connect(self.close)  # type: ignore

        layout.addWidget(self.close_button)

        self._drag_pos: Optional[QPoint] = None
        self.text_requested.connect(self._apply_text)
        self.show()

    def display_text(self, text: str) -> None:
        if text.strip():
            self.text_requested.emit(text)

    def _apply_text(self, text: str) -> None:
        self.label.setText(text)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            event.accept()
        super().mouseReleaseEvent(event)
