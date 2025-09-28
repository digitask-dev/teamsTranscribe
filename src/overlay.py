from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import (
    QLabel,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 12, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.label = QLabel(self)
        self.label.setStyleSheet("font-size: 20px; color: white;")
        self.label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        header_layout.addWidget(self.label, 1)

        self.toggle_button = QPushButton(self)
        self.toggle_button.setFixedSize(24, 24)
        self.toggle_button.setStyleSheet(
            "color: white; background-color: rgba(255, 255, 255, 40);"
            "border: none; font-size: 14px;"
        )
        self.toggle_button.setCursor(Qt.PointingHandCursor)  # type: ignore
        self.toggle_button.clicked.connect(self._toggle_info_visibility)  # type: ignore

        header_layout.addWidget(self.toggle_button)

        self.close_button = QPushButton("X", self)
        self.close_button.setFixedSize(24, 24)
        self.close_button.setStyleSheet(
            "color: white; background-color: rgba(255, 255, 255, 60);"
            "border: none; font-size: 14px;"
        )
        self.close_button.setCursor(Qt.PointingHandCursor)  # type: ignore
        self.close_button.clicked.connect(self.close)  # type: ignore

        header_layout.addWidget(self.close_button)

        layout.addLayout(header_layout)

        self.info_label = QLabel(self)
        self.info_label.setStyleSheet(
            "font-size: 12px; color: rgba(255, 255, 255, 0.75);"
            "background-color: rgba(31, 31, 30, 1); padding: 4px 8px; border-radius: 4px;"
        )
        self.info_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)

        layout.addWidget(self.info_label)

        self._drag_pos: Optional[QPoint] = None
        self._info_visible = False
        self._set_toggle_arrow()
        self.text_requested.connect(self._apply_text)
        self.show()

    def display_text(self, text: str) -> None:
        if text.strip():
            self.text_requested.emit(text)

    def set_status_info(self, model: str, language: Optional[str], compute_type: str) -> None:
        language_display = language if language else "Auto"
        self.info_label.setText(
            f"Model: {model}    Language: {language_display}    Compute: {compute_type}"
        )

    def _set_toggle_arrow(self) -> None:
        self.toggle_button.setText("\u25B4" if self._info_visible else "\u25BE")

    def _toggle_info_visibility(self) -> None:
        self._info_visible = not self._info_visible
        self.info_label.setVisible(self._info_visible)
        self._set_toggle_arrow()

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




