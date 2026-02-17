"""Small colored LED circle indicator."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QSize

from ui.styles import COLOR_OK, COLOR_WARN, COLOR_FAIL, COLOR_INACTIVE


class LedIndicator(QWidget):
    """A 16px colored circle used as a status LED."""

    COLORS = {
        "green": COLOR_OK,
        "yellow": COLOR_WARN,
        "red": COLOR_FAIL,
        "gray": COLOR_INACTIVE,
    }

    def __init__(self, color: str = "gray", size: int = 16, parent=None):
        super().__init__(parent)
        self._color = self.COLORS.get(color, COLOR_INACTIVE)
        self._size = size
        self.setFixedSize(QSize(size, size))

    def set_color(self, color: str):
        self._color = self.COLORS.get(color, COLOR_INACTIVE)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(self._color).darker(130), 1))
        painter.setBrush(QBrush(QColor(self._color)))
        margin = 1
        painter.drawEllipse(margin, margin, self._size - 2 * margin, self._size - 2 * margin)
        painter.end()
