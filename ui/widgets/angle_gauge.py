"""Circular gauge widget for displaying roll/pitch/yaw angles."""
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient
from PyQt6.QtCore import Qt, QRectF, QPointF

from ui.styles import SURFACE0, SURFACE1, TEXT, SUBTEXT0, BLUE, GREEN, YELLOW, RED


class AngleGauge(QWidget):
    """Circular gauge showing an angle with needle, ticks, and numeric readout."""

    def __init__(self, title: str = "Axis", min_angle: float = -180, max_angle: float = 180, parent=None):
        super().__init__(parent)
        self._title = title
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._angle = 0.0
        self._target = None
        self._frame_angle = None
        self.setMinimumSize(160, 180)

    def set_angle(self, angle: float):
        self._angle = angle
        self.update()

    def set_target(self, target: float | None):
        self._target = target
        self.update()

    def set_frame_angle(self, angle: float | None):
        self._frame_angle = angle
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        gauge_r = min(w, h - 30) / 2 - 10
        cy = 10 + gauge_r

        # Background circle
        painter.setPen(QPen(QColor(SURFACE1), 2))
        painter.setBrush(QColor(SURFACE0))
        painter.drawEllipse(QPointF(cx, cy), gauge_r, gauge_r)

        # Tick marks
        painter.setPen(QPen(QColor(SUBTEXT0), 1))
        tick_font = QFont("sans-serif", 8)
        painter.setFont(tick_font)
        for deg in range(-180, 181, 45):
            rad = math.radians(deg - 90)
            inner_r = gauge_r - 10
            outer_r = gauge_r - 3
            x1 = cx + inner_r * math.cos(rad)
            y1 = cy + inner_r * math.sin(rad)
            x2 = cx + outer_r * math.cos(rad)
            y2 = cy + outer_r * math.sin(rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            if deg % 90 == 0:
                label_r = gauge_r - 20
                lx = cx + label_r * math.cos(rad) - 10
                ly = cy + label_r * math.sin(rad) - 6
                painter.drawText(QRectF(lx, ly, 20, 12), Qt.AlignmentFlag.AlignCenter, str(deg))

        # Target needle (if set)
        if self._target is not None:
            self._draw_needle(painter, cx, cy, gauge_r - 15, self._target, QColor(YELLOW), 2)

        # Frame angle needle (if set)
        if self._frame_angle is not None:
            self._draw_needle(painter, cx, cy, gauge_r - 20, self._frame_angle, QColor(GREEN), 2)

        # Main needle (IMU angle)
        self._draw_needle(painter, cx, cy, gauge_r - 12, self._angle, QColor(BLUE), 3)

        # Center dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(TEXT))
        painter.drawEllipse(QPointF(cx, cy), 4, 4)

        # Title
        title_font = QFont("sans-serif", 10, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(SUBTEXT0))
        painter.drawText(QRectF(0, cy + gauge_r + 2, w, 18), Qt.AlignmentFlag.AlignCenter, self._title)

        # Numeric readout
        val_font = QFont("sans-serif", 14, QFont.Weight.Bold)
        painter.setFont(val_font)
        painter.setPen(QColor(TEXT))
        painter.drawText(QRectF(0, cy - 14, w, 28), Qt.AlignmentFlag.AlignCenter, f"{self._angle:.1f}")

        painter.end()

    def _draw_needle(self, painter: QPainter, cx: float, cy: float, length: float, angle: float, color: QColor, width: int):
        rad = math.radians(angle - 90)
        x = cx + length * math.cos(rad)
        y = cy + length * math.sin(rad)
        painter.setPen(QPen(color, width))
        painter.drawLine(QPointF(cx, cy), QPointF(x, y))
